import cv2
import mediapipe as mp
import time
import threading

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

GAME_WIDTH = 1280
GAME_HEIGHT = 720
VISIBILITY_THRESHOLD = 0.6
ALPHA = 0.4  # EMA smoothing factor

SHOW_DEBUG_WINDOW = True  # set False for a clean run with no window

class VisionTracker:
    def __init__(self):
        self.pose = mp_pose.Pose(
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.X_MIN, self.X_MAX = 0.05, 0.95  # fallback defaults if calibration skipped
        self.Y_MIN, self.Y_MAX = 0.10, 0.90

        self._lock = threading.Lock()
        self._pos = (GAME_WIDTH // 2, GAME_HEIGHT // 2)  # default center
        self._smoothed_x, self._smoothed_y = None, None
        self._running = False
        self._thread = None

    def _normalize_and_clamp(self, value, v_min, v_max):
        if v_max - v_min == 0:
            return 0.5
        scaled = (value - v_min) / (v_max - v_min)
        return max(0.0, min(1.0, scaled))

    def warmup(self, duration=2.0):
        start = time.time()
        while time.time() - start < duration:
            ret, frame = self.cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.pose.process(rgb)
            if SHOW_DEBUG_WINDOW:
                remaining = duration - (time.time() - start)
                cv2.putText(frame, "Get ready...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"{remaining:.1f}s", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                cv2.imshow("Pose Test", frame)
                cv2.waitKey(1)

    def calibrate(self, duration=5.0):
        ret, sample_frame = self.cap.read()
        h, w = sample_frame.shape[:2]

        x_min, x_max = 1.0, 0.0
        y_min, y_max = 1.0, 0.0

        start = time.time()
        while time.time() - start < duration:
            ret, frame = self.cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb)

            remaining = duration - (time.time() - start)

            if results.pose_landmarks:
                if SHOW_DEBUG_WINDOW:
                    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                wrist = results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST]
                if wrist.visibility > VISIBILITY_THRESHOLD:
                    x_min = min(x_min, wrist.x)
                    x_max = max(x_max, wrist.x)
                    y_min = min(y_min, wrist.y)
                    y_max = max(y_max, wrist.y)

            if SHOW_DEBUG_WINDOW:
                cv2.putText(frame, "Wave hand around your FULL play area", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(frame, "(reach all 4 corners + edges)", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
                cv2.putText(frame, f"{remaining:.1f}s", (w - 100, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                cv2.imshow("Pose Test", frame)
                cv2.waitKey(1)

        margin = 0.03
        # only commit calibration if we actually got a reasonable spread
        if (x_max - x_min) > 0.1 and (y_max - y_min) > 0.1:
            self.X_MIN = max(0, x_min - margin)
            self.X_MAX = min(1, x_max + margin)
            self.Y_MIN = max(0, y_min - margin)
            self.Y_MAX = min(1, y_max + margin)
        print(f"Calibrated: X({self.X_MIN:.2f}-{self.X_MAX:.2f}) Y({self.Y_MIN:.2f}-{self.Y_MAX:.2f})")

    def _loop(self):
        prev_time = 0
        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb_frame)

            if results.pose_landmarks:
                wrist = results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST]

                norm_x = self._normalize_and_clamp(wrist.x, self.X_MIN, self.X_MAX)
                norm_y = self._normalize_and_clamp(wrist.y, self.Y_MIN, self.Y_MAX)

                raw_x = norm_x * GAME_WIDTH
                raw_y = norm_y * GAME_HEIGHT

                if self._smoothed_x is None:
                    self._smoothed_x, self._smoothed_y = raw_x, raw_y
                else:
                    self._smoothed_x = ALPHA * raw_x + (1 - ALPHA) * self._smoothed_x
                    self._smoothed_y = ALPHA * raw_y + (1 - ALPHA) * self._smoothed_y

                with self._lock:
                    self._pos = (int(self._smoothed_x), int(self._smoothed_y))
            # NOTE: no cv2.imshow/waitKey here — OpenCV's GUI calls are not thread-safe
            # on macOS and must only run on the main thread (handled in warmup/calibrate).

    def start(self):
        """Runs warmup + calibration (blocking, ~7 sec total), then starts the background tracking thread."""
        self.warmup()
        self.calibrate()
        if SHOW_DEBUG_WINDOW:
            cv2.destroyAllWindows()
            for _ in range(5):
                cv2.waitKey(1)  # flush pending window-close events on macOS
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        self.cap.release()
        if SHOW_DEBUG_WINDOW:
            cv2.destroyAllWindows()

    def get_player_position(self):
        with self._lock:
            return self._pos


# ---- Module-level singleton so teammate can just import and call ----
_tracker = None

def init_tracker():
    """Call once at game startup. Runs warmup + calibration, then starts background tracking."""
    global _tracker
    _tracker = VisionTracker()
    _tracker.start()

def get_player_position():
    """Returns latest (x, y) in game screen pixel coordinates. Call every frame — non-blocking."""
    if _tracker is None:
        raise RuntimeError("Call init_tracker() before get_player_position()")
    return _tracker.get_player_position()

def shutdown_tracker():
    if _tracker is not None:
        _tracker.stop()


# ---- Standalone test ----
if __name__ == "__main__":
    init_tracker()
    print("Tracking started. Press Ctrl+C to stop.")
    try:
        while True:
            x, y = get_player_position()
            print(f"Player pos: x={x}, y={y}")
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown_tracker()