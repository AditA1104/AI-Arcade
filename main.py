import math
from pathlib import Path
import random
import sqlite3
from datetime import datetime

import pygame

from input import get_player_position
from leaderboard import initialize_database, add_score, get_top_scores
from sprites import make_fruit_sprite, make_bomb_sprite, make_custom_fruit_sprite


# ============================================================
# CONFIG
# ============================================================

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
FIXED_DT = 1.0 / 60.0

GAME_DURATION = 60.0
FRUIT_RADIUS = 32
PLAYER_RADIUS = 16
TRAIL_LENGTH = 8
COMBO_TIMEOUT = 1.2


# ============================================================
# GAME STATES
# ============================================================

START = "START"
PLAYING = "PLAYING"
GAME_OVER = "GAME_OVER"
NAME_ENTRY = "NAME_ENTRY"
LEADERBOARD = "LEADERBOARD"
RESET_CONFIRM = "RESET_CONFIRM"
BOMB_BLAST = "BOMB_BLAST"

game_state = START


# ============================================================
# COLORS
# ============================================================

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

BACKGROUND_COLOR = (10, 12, 24)

FRUIT_COLORS = {
    "apple": (235, 55, 70),
    "orange": (255, 145, 35),
    "banana": (255, 215, 45),
    "pineapple": (225, 155, 35),
    "watermelon": (55, 205, 100),
}

FRUIT_DARK = {
    "apple": (150, 25, 45),
    "orange": (190, 75, 15),
    "banana": (170, 120, 15),
    "pineapple": (160, 90, 15),
    "watermelon": (25, 125, 65),
}

FRUIT_TYPES = [
    "apple",
    "orange",
    "banana",
    "pineapple",
    "watermelon",
]

BOMB_CHANCE = 0.10



# ============================================================
# UTILITY
# ============================================================

def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def distance_point_to_segment(px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)

    t = ((px - x1) * dx + (py - y1) * dy) / (
        dx * dx + dy * dy
    )

    t = clamp(t, 0.0, 1.0)

    closest_x = x1 + t * dx
    closest_y = y1 + t * dy

    return math.hypot(
        px - closest_x,
        py - closest_y,
    )


# ============================================================
# PARTICLE
# ============================================================

class Particle:
    def __init__(
        self,
        x,
        y,
        color,
        speed=None,
        size=None,
    ):
        self.x = x
        self.y = y

        angle = random.uniform(0, math.tau)

        if speed is None:
            speed = random.uniform(80, 350)

        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

        self.size = (
            size
            if size is not None
            else random.uniform(2, 6)
        )

        self.life = random.uniform(0.35, 0.8)
        self.max_life = self.life

        self.color = color

        self.gravity = random.uniform(
            200,
            500,
        )

    def update(self, dt):
        self.vy += self.gravity * dt

        self.x += self.vx * dt
        self.y += self.vy * dt

        self.life -= dt

    def draw(self, surface):
        if self.life <= 0:
            return

        alpha = int(
            255 * self.life / self.max_life
        )

        radius = max(
            1,
            int(
                self.size
                * self.life
                / self.max_life
            ),
        )

        glow = pygame.Surface(
            (radius * 8, radius * 8),
            pygame.SRCALPHA,
        )

        pygame.draw.circle(
            glow,
            (*self.color, alpha // 3),
            (
                radius * 4,
                radius * 4,
            ),
            radius * 3,
        )

        pygame.draw.circle(
            glow,
            (*self.color, alpha),
            (
                radius * 4,
                radius * 4,
            ),
            radius,
        )

        surface.blit(
            glow,
            (
                int(self.x - radius * 4),
                int(self.y - radius * 4),
            ),
        )


# ============================================================
# FLOATING TEXT
# ============================================================

class FloatingText:
    def __init__(
        self,
        text,
        x,
        y,
        color=WHITE,
        size=32,
    ):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.size = size

        self.life = 0.8
        self.max_life = self.life

        self.velocity = -75
        self.scale = 0.4

    def update(self, dt):
        self.y += self.velocity * dt
        self.life -= dt

        progress = (
            1.0
            - self.life / self.max_life
        )

        if progress < 0.2:
            self.scale = (
                0.4
                + progress * 3.0
            )
        else:
            self.scale = 1.0

    def draw(self, surface, font):
        if self.life <= 0:
            return

        alpha = int(
            255
            * self.life
            / self.max_life
        )

        rendered = font.render(
            self.text,
            True,
            self.color,
        )

        rendered = pygame.transform.rotozoom(
            rendered,
            0,
            self.scale,
        )

        rendered.set_alpha(alpha)

        rect = rendered.get_rect(
            center=(
                int(self.x),
                int(self.y),
            )
        )

        surface.blit(
            rendered,
            rect,
        )


# ============================================================
# SLASH EFFECT
# ============================================================

class SlashEffect:
    def __init__(self, points):
        self.points = list(points)

        self.life = 0.12
        self.max_life = self.life

    def update(self, dt):
        self.life -= dt

    def draw(self, surface):
        if len(self.points) < 2:
            return

        progress = (
            self.life
            / self.max_life
        )

        overlay = pygame.Surface(
            (
                SCREEN_WIDTH,
                SCREEN_HEIGHT,
            ),
            pygame.SRCALPHA,
        )

        points = [
            (int(x), int(y))
            for x, y in self.points
        ]

        width = max(
            2,
            int(10 * progress),
        )

        pygame.draw.lines(
            overlay,
            (
                255,
                255,
                255,
                int(230 * progress),
            ),
            False,
            points,
            width,
        )

        surface.blit(
            overlay,
            (0, 0),
        )


# ============================================================
# ACTUAL FRUIT HALF
# ============================================================

class FruitHalf:
    def __init__(self, x, y, fruit_type, direction, cut_angle, fruit_scale=1.0):
        self.x = x
        self.y = y
        self.fruit_type = fruit_type
        self.direction = direction
        self.cut_angle = cut_angle
        self.fruit_scale = fruit_scale

        angle = math.radians(cut_angle)
        normal_x = -math.sin(angle)
        normal_y = math.cos(angle)

        self.vx = normal_x * direction * random.uniform(90, 150)
        self.vy = normal_y * direction * random.uniform(40, 80)

        self.gravity = 550
        self.rotation = 0
        self.rotation_speed = direction * random.uniform(140, 260)

        self.life = 0.85
        self.max_life = self.life

    def update(self, dt):
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rotation += self.rotation_speed * dt
        self.life -= dt

    def draw(self, surface):
        if self.life <= 0:
            return

        alpha = int(
            255 * clamp(
                self.life / self.max_life,
                0,
                1
            )
        )

        size = int(100 * self.fruit_scale)

        # Apple uses the imported half-cut asset.
        if self.fruit_type == "apple":
            half_file = Path(
                "fruit_assets",
                "game",
                "half_apple.png"
            )

            if not half_file.exists():
                return

            image = pygame.image.load(
                str(half_file)
            ).convert_alpha()

            whole = make_custom_fruit_sprite(
                "apple",
                size
            )

            if whole is None:
                return

            target_height = whole.get_height()
            scale_factor = target_height / image.get_height()

            image = pygame.transform.smoothscale(
                image,
                (
                    max(1, int(image.get_width() * scale_factor)),
                    max(1, int(image.get_height() * scale_factor))
                )
            )

            image.set_alpha(alpha)

            image = pygame.transform.rotate(
                image,
                self.rotation
            )

            rect = image.get_rect(
                center=(
                    int(self.x),
                    int(self.y)
                )
            )

            surface.blit(image, rect)
            return

        # Use the imported whole fruit for all other fruits.
        whole = make_custom_fruit_sprite(
            self.fruit_type,
            size
        )

        if whole is None:
            return

        whole = whole.convert_alpha()

        width = whole.get_width()
        height = whole.get_height()

        cx = width / 2
        cy = height / 2

        # Pineapple is tall, so split it left/right.
        if self.fruit_type == "pineapple":
            if self.direction < 0:
                polygon = [
                    (0, 0),
                    (width, 0),
                    (width, cy),
                    (0, cy)
                ]
            else:
                polygon = [
                    (0, cy),
                    (width, cy),
                    (width, height),
                    (0, height)
                ]

        else:
            # Cut other fruits along the actual slash angle.
            angle = math.radians(self.cut_angle)

            dx = math.cos(angle)
            dy = math.sin(angle)

            px = -dy
            py = dx

            big = max(width, height) * 3

            if self.direction < 0:
                polygon = [
                    (
                        cx - dx * big - px * big,
                        cy - dy * big - py * big
                    ),
                    (
                        cx + dx * big - px * big,
                        cy + dy * big - py * big
                    ),
                    (
                        cx + dx * big,
                        cy + dy * big
                    ),
                    (
                        cx - dx * big,
                        cy - dy * big
                    )
                ]
            else:
                polygon = [
                    (
                        cx + dx * big + px * big,
                        cy + dy * big + py * big
                    ),
                    (
                        cx - dx * big + px * big,
                        cy - dy * big + py * big
                    ),
                    (
                        cx - dx * big,
                        cy - dy * big
                    ),
                    (
                        cx + dx * big,
                        cy + dy * big
                    )
                ]

        # Create a clean alpha mask.
        mask_surface = pygame.Surface(
            (width, height),
            pygame.SRCALPHA
        )

        mask_surface.fill(
            (0, 0, 0, 0)
        )

        pygame.draw.polygon(
            mask_surface,
            (255, 255, 255, 255),
            polygon
        )

        # Apply the mask to the original fruit.
        masked = pygame.Surface(
            (width, height),
            pygame.SRCALPHA
        )

        masked.blit(
            whole,
            (0, 0)
        )

        masked.blit(
            mask_surface,
            (0, 0),
            special_flags=pygame.BLEND_RGBA_MULT
        )

        masked.set_alpha(alpha)

        masked = pygame.transform.rotate(
            masked,
            self.rotation
        )

        rect = masked.get_rect(
            center=(
                int(self.x),
                int(self.y)
            )
        )

        surface.blit(
            masked,
            rect
        )

class Fruit:
    def __init__(self):
        self.x = random.randint(
            100,
            SCREEN_WIDTH - 100,
        )

        self.y = SCREEN_HEIGHT + 60

        self.radius = FRUIT_RADIUS

        self.is_bomb = random.random() < BOMB_CHANCE

        if self.is_bomb:
            self.fruit_type = "bomb"
        else:
            self.fruit_type = random.choice(FRUIT_TYPES)

        self.vx = random.uniform(
            -160,
            160,
        )

        self.vy = random.uniform(
            -850,
            -650,
        )

        self.gravity = random.uniform(
            800,
            1050,
        )

        self.rotation = random.uniform(
            0,
            360,
        )

        self.rotation_speed = random.uniform(
            -240,
            240,
        )

        self.alive = True

        self.scale = 1.0

    def update(self, dt):
        self.vy += (
            self.gravity * dt
        )

        self.x += (
            self.vx * dt
        )

        self.y += (
            self.vy * dt
        )

        self.rotation += (
            self.rotation_speed
            * dt
        )

        if (
            self.x < -100
            or self.x
            > SCREEN_WIDTH + 100
            or self.y
            > SCREEN_HEIGHT + 100
        ):
            self.alive = False

    def draw(self, surface):
        size = int(100 * self.scale)

        if self.is_bomb:
            sprite = make_bomb_sprite(size, total_time)
        else:
            sprite = make_custom_fruit_sprite(
                self.fruit_type,
                size
            )

        # Scale slightly based on flight direction.
        # This gives a pseudo-3D squash/stretch effect.
        flight_scale = 1.0

        if abs(self.vy) > 500:
            flight_scale = 1.0 + min(
                0.12,
                abs(self.vy) / 7000
            )

        sprite = pygame.transform.smoothscale(
            sprite,
            (
                int(sprite.get_width() * flight_scale),
                int(sprite.get_height() / flight_scale)
            )
        )

        # Rotate while airborne.
        sprite = pygame.transform.rotate(
            sprite,
            self.rotation
        )

        rect = sprite.get_rect(
            center=(
                int(self.x),
                int(self.y)
            )
        )

        surface.blit(
            sprite,
            rect
        )



# ============================================================
# RESET GAME
# ============================================================

def reset_game():
    global score
    global combo
    global combo_timer
    global game_time
    global fruits
    global particles
    global floating_texts
    global fruit_halves
    global slash_effects
    global player_trail
    global spawn_timer
    global screen_shake

    score = 0
    combo = 0
    combo_timer = 0.0

    game_time = GAME_DURATION

    fruits = []
    particles = []
    floating_texts = []
    fruit_halves = []
    slash_effects = []

    player_trail = []

    spawn_timer = 0.0
    screen_shake = 0.0


# ============================================================
# DATABASE RESET
# ============================================================

def reset_leaderboard():
    connection = sqlite3.connect(
        "leaderboard.db"
    )

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM leaderboard"
    )

    connection.commit()
    connection.close()


# ============================================================
# PYGAME SETUP
# ============================================================

pygame.init()

screen = pygame.display.set_mode(
    (
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
    )
)

pygame.display.set_caption(
    "Pose-Controlled AI Arcade"
)

clock = pygame.time.Clock()

pygame.mouse.set_visible(True)

initialize_database()

font_small = pygame.font.Font(
    None,
    28,
)

font_medium = pygame.font.Font(
    None,
    42,
)

font_large = pygame.font.Font(
    None,
    72,
)

font_huge = pygame.font.Font(
    None,
    110,
)


# ============================================================
# GAME VARIABLES
# ============================================================

score = 0
combo = 0
combo_timer = 0.0

game_time = GAME_DURATION

fruits = []
particles = []
floating_texts = []
fruit_halves = []
slash_effects = []

player_x = SCREEN_WIDTH // 2
player_y = SCREEN_HEIGHT // 2

previous_x = player_x
previous_y = player_y

player_trail = []

spawn_timer = 0.0
screen_shake = 0.0

name_input = ""

leaderboard_return_timer = 0.0

bomb_blast_timer = 0.0
bomb_blast_x = SCREEN_WIDTH // 2
bomb_blast_y = SCREEN_HEIGHT // 2


# ============================================================
# BACKGROUND
# ============================================================

background_particles = []

for _ in range(90):

    background_particles.append(
        {
            "x": random.randint(
                0,
                SCREEN_WIDTH,
            ),
            "y": random.randint(
                0,
                SCREEN_HEIGHT,
            ),
            "size": random.randint(
                1,
                3,
            ),
            "speed": random.uniform(
                5,
                20,
            ),
            "phase": random.uniform(
                0,
                math.tau,
            ),
        }
    )


def draw_background(
    surface,
    time_value,
):

    surface.fill(
        BACKGROUND_COLOR
    )

    for i in range(9):

        y = i * 90

        alpha = (
            15
            + int(
                10
                * math.sin(
                    time_value
                    * 0.7
                    + i
                )
            )
        )

        band = pygame.Surface(
            (
                SCREEN_WIDTH,
                90,
            ),
            pygame.SRCALPHA,
        )

        pygame.draw.rect(
            band,
            (
                40,
                50,
                100,
                alpha,
            ),
            band.get_rect(),
        )

        surface.blit(
            band,
            (0, y),
        )

    grid_offset = int(
        (
            time_value
            * 25
        )
        % 80
    )

    for x in range(
        -80,
        SCREEN_WIDTH + 80,
        80,
    ):

        pygame.draw.line(
            surface,
            (25, 30, 55),
            (x, 0),
            (
                x,
                SCREEN_HEIGHT,
            ),
            1,
        )

    for y in range(
        -80,
        SCREEN_HEIGHT + 80,
        80,
    ):

        pygame.draw.line(
            surface,
            (25, 30, 55),
            (
                0,
                y + grid_offset,
            ),
            (
                SCREEN_WIDTH,
                y + grid_offset,
            ),
            1,
        )

    for particle in background_particles:

        px = particle["x"]

        py = (
            particle["y"]
            - time_value
            * particle["speed"]
        ) % SCREEN_HEIGHT

        pulse = (
            0.5
            + 0.5
            * math.sin(
                time_value * 2
                + particle["phase"]
            )
        )

        radius = max(
            1,
            int(
                particle["size"]
                * pulse
            ),
        )

        pygame.draw.circle(
            surface,
            (70, 80, 120),
            (
                int(px),
                int(py),
            ),
            radius,
        )


# ============================================================
# MAIN LOOP
# ============================================================

running = True

accumulator = 0.0
total_time = 0.0

while running:

    frame_time = (
        clock.tick(FPS)
        / 1000.0
    )

    frame_time = min(
        frame_time,
        0.1,
    )

    accumulator += frame_time
    total_time += frame_time

    # ========================================================
    # EVENTS
    # ========================================================

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:

                if game_state == RESET_CONFIRM:
                    game_state = LEADERBOARD
                else:
                    running = False

            if game_state == START:

                if event.key == pygame.K_RETURN:

                    reset_game()

                    game_state = PLAYING

            elif game_state == GAME_OVER:

                if event.key == pygame.K_RETURN:

                    name_input = ""

                    game_state = NAME_ENTRY

            elif game_state == NAME_ENTRY:

                if event.key == pygame.K_BACKSPACE:

                    name_input = (
                        name_input[:-1]
                    )

                elif event.key == pygame.K_RETURN:

                    if name_input.strip():

                        add_score(
                            name_input.strip(),
                            score,
                        )

                        leaderboard_return_timer = 10.0

                        game_state = LEADERBOARD

                elif event.unicode.isprintable():

                    if len(name_input) < 12:

                        name_input += (
                            event.unicode
                        )

            elif game_state == LEADERBOARD:

                if event.key == pygame.K_RETURN:

                    game_state = START

                elif event.key == pygame.K_r:

                    game_state = RESET_CONFIRM

            elif game_state == RESET_CONFIRM:

                if event.key == pygame.K_y:

                    reset_leaderboard()

                    game_state = LEADERBOARD

                elif event.key == pygame.K_n:

                    game_state = LEADERBOARD


    # ========================================================
    # FIXED UPDATE
    # ========================================================

    while accumulator >= FIXED_DT:

        dt = FIXED_DT

        # ====================================================
        # START
        # ====================================================

        if game_state == START:

            x, y = get_player_position()

            movement = math.hypot(
                x - previous_x,
                y - previous_y,
            )

            previous_x = x
            previous_y = y

            if movement > 12:

                reset_game()

                game_state = PLAYING

        # ====================================================
        # PLAYING
        # ====================================================

        elif game_state == PLAYING:

            new_x, new_y = (
                get_player_position()
            )

            new_x = int(
                clamp(
                    new_x,
                    0,
                    SCREEN_WIDTH,
                )
            )

            new_y = int(
                clamp(
                    new_y,
                    0,
                    SCREEN_HEIGHT,
                )
            )

            movement = math.hypot(
                new_x - player_x,
                new_y - player_y,
            )

            previous_x = player_x
            previous_y = player_y

            player_x = new_x
            player_y = new_y

            if movement > 2:

                player_trail.append(
                    (
                        player_x,
                        player_y,
                    )
                )

                if len(player_trail) > TRAIL_LENGTH:

                    player_trail.pop(0)

            if movement > 12:

                slash_effects.append(
                    SlashEffect(
                        player_trail
                    )
                )

            combo_timer -= dt

            if combo_timer <= 0:

                combo = 0

            game_time -= dt

            if game_time <= 0:

                game_time = 0

                game_state = GAME_OVER

            spawn_timer -= dt

            elapsed = (
                GAME_DURATION
                - game_time
            )

            spawn_interval = max(
                0.34,
                0.82
                - elapsed
                * 0.007,
            )

            if spawn_timer <= 0:

                fruits.append(
                    Fruit()
                )

                spawn_timer = (
                    spawn_interval
                )

            for fruit in fruits:

                fruit.update(dt)

            fruits = [
                fruit
                for fruit in fruits
                if fruit.alive
            ]

            if len(player_trail) >= 2:

                x1, y1 = (
                    player_trail[-2]
                )

                x2, y2 = (
                    player_trail[-1]
                )

                for fruit in fruits:

                    if not fruit.alive:
                        continue

                    distance = (
                        distance_point_to_segment(
                            fruit.x,
                            fruit.y,
                            x1,
                            y1,
                            x2,
                            y2,
                        )
                    )

                    if distance <= (
                        fruit.radius + 8
                    ):

                        if fruit.is_bomb:
                            fruit.alive = False

                            # Start bomb blast sequence
                            bomb_blast_timer = 0.0
                            bomb_blast_x = fruit.x
                            bomb_blast_y = fruit.y

                            game_state = BOMB_BLAST

                            screen_shake = 30

                            # Initial explosion burst
                            for _ in range(90):

                                angle = random.uniform(
                                    0,
                                    math.tau
                                )

                                speed = random.uniform(
                                    180,
                                    700
                                )

                                particles.append(
                                    Particle(
                                        fruit.x,
                                        fruit.y,
                                        random.choice(
                                            [
                                                (
                                                    255,
                                                    35,
                                                    25
                                                ),
                                                (
                                                    255,
                                                    100,
                                                    20
                                                ),
                                                (
                                                    255,
                                                    210,
                                                    50
                                                ),
                                                WHITE
                                            ]
                                        ),
                                        speed=speed,
                                        size=random.uniform(
                                            3,
                                            11
                                        )
                                    )
                                )

                            floating_texts.append(
                                FloatingText(
                                    "BOMB!",
                                    fruit.x,
                                    fruit.y,
                                    (
                                        255,
                                        50,
                                        50
                                    ),
                                    65
                                )
                            )

                            continue

                        fruit.alive = False

                        combo += 1

                        combo_timer = (
                            COMBO_TIMEOUT
                        )

                        multiplier = min(
                            combo,
                            5,
                        )

                        gained = (
                            10
                            * multiplier
                        )

                        score += gained

                        # Calculate slash direction
                        slash_dx = (
                            x2 - x1
                        )

                        slash_dy = (
                            y2 - y1
                        )

                        cut_angle = math.degrees(
                            math.atan2(
                                slash_dy,
                                slash_dx,
                            )
                        )

                        # Actual halves
                        fruit_halves.append(
                            FruitHalf(
                                fruit.x,
                                fruit.y,
                                fruit.fruit_type,
                                -1,
                                cut_angle,
                                fruit.scale,
                            )
                        )

                        fruit_halves.append(
                            FruitHalf(
                                fruit.x,
                                fruit.y,
                                fruit.fruit_type,
                                1,
                                cut_angle,
                                fruit.scale,
                            )
                        )

                        fruit_color = (
                            FRUIT_COLORS[
                                fruit.fruit_type
                            ]
                        )

                        # Juice
                        for _ in range(32):

                            particles.append(
                                Particle(
                                    fruit.x,
                                    fruit.y,
                                    fruit_color,
                                    speed=random.uniform(
                                        100,
                                        430,
                                    ),
                                    size=random.uniform(
                                        2,
                                        7,
                                    ),
                                )
                            )

                        # Bright impact sparks
                        for _ in range(12):

                            particles.append(
                                Particle(
                                    fruit.x,
                                    fruit.y,
                                    WHITE,
                                    speed=random.uniform(
                                        180,
                                        420,
                                    ),
                                    size=random.uniform(
                                        1,
                                        4,
                                    ),
                                )
                            )

                        floating_texts.append(
                            FloatingText(
                                "+"
                                + str(gained),
                                fruit.x,
                                fruit.y,
                                WHITE,
                                38,
                            )
                        )

                        if combo >= 2:

                            floating_texts.append(
                                FloatingText(
                                    "COMBO x"
                                    + str(
                                        multiplier
                                    ),
                                    fruit.x,
                                    fruit.y - 42,
                                    fruit_color,
                                    30,
                                )
                            )

                        screen_shake = min(
                            14,
                            screen_shake
                            + 3
                            + combo * 0.4,
                        )

            fruits = [
                fruit
                for fruit in fruits
                if fruit.alive
            ]

            for particle in particles:

                particle.update(dt)

            particles = [
                particle
                for particle in particles
                if particle.life > 0
            ]

            for text in floating_texts:

                text.update(dt)

            floating_texts = [
                text
                for text in floating_texts
                if text.life > 0
            ]

            for half in fruit_halves:

                half.update(dt)

            fruit_halves = [
                half
                for half in fruit_halves
                if half.life > 0
            ]

            for effect in slash_effects:

                effect.update(dt)

            slash_effects = [
                effect
                for effect in slash_effects
                if effect.life > 0
            ]

            screen_shake *= 0.88

            if screen_shake < 0.2:

                screen_shake = 0

        # ====================================================
        # BOMB BLAST
        # ====================================================

        elif game_state == BOMB_BLAST:

            bomb_blast_timer += dt

            screen_shake *= 0.94

            # Keep particles moving during explosion
            for particle in particles:
                particle.update(dt)

            particles = [
                particle
                for particle in particles
                if particle.life > 0
            ]

            for text in floating_texts:
                text.update(dt)

            floating_texts = [
                text
                for text in floating_texts
                if text.life > 0
            ]

            # Explosion lasts 0.9 seconds
            if bomb_blast_timer >= 0.9:

                game_time = 0

                game_state = GAME_OVER

                screen_shake = 0

        # ====================================================
        # LEADERBOARD
        # ====================================================

        elif game_state == LEADERBOARD:

            leaderboard_return_timer -= dt

            if (
                leaderboard_return_timer <= 0
                and leaderboard_return_timer != 0
            ):

                game_state = START

        accumulator -= dt

    # ========================================================
    # DRAW
    # ========================================================

    draw_background(
        screen,
        total_time,
    )

    shake_x = 0
    shake_y = 0

    if screen_shake > 0:

        shake_x = random.randint(
            -int(screen_shake),
            int(screen_shake),
        )

        shake_y = random.randint(
            -int(screen_shake),
            int(screen_shake),
        )

    world = pygame.Surface(
        (
            SCREEN_WIDTH,
            SCREEN_HEIGHT,
        ),
        pygame.SRCALPHA,
    )

    # ========================================================
    # PLAYING
    # ========================================================

    if game_state == PLAYING:

        for fruit in fruits:

            fruit.draw(world)

        for half in fruit_halves:

            half.draw(world)

        for particle in particles:

            particle.draw(world)

        # Slash trail
        if len(player_trail) >= 2:

            for i in range(
                1,
                len(player_trail),
            ):

                x1, y1 = (
                    player_trail[i - 1]
                )

                x2, y2 = (
                    player_trail[i]
                )

                progress = (
                    i
                    / len(player_trail)
                )

                width = max(
                    2,
                    int(
                        14 * progress
                    ),
                )

                alpha = int(
                    210 * progress
                )

                pygame.draw.line(
                    world,
                    (
                        255,
                        255,
                        255,
                        alpha,
                    ),
                    (
                        int(x1),
                        int(y1),
                    ),
                    (
                        int(x2),
                        int(y2),
                    ),
                    width,
                )

        # Player
        pygame.draw.circle(
            world,
            (190, 70, 255),
            (
                player_x,
                player_y,
            ),
            PLAYER_RADIUS,
        )

        for text in floating_texts:

            text.draw(
                world,
                font_medium,
            )

        for effect in slash_effects:

            effect.draw(world)

        # HUD
        score_surface = font_large.render(
            str(score),
            True,
            WHITE,
        )

        screen.blit(
            score_surface,
            (
                35 + shake_x,
                25 + shake_y,
            ),
        )

        score_label = font_small.render(
            "SCORE",
            True,
            (130, 140, 180),
        )

        screen.blit(
            score_label,
            (
                40 + shake_x,
                82 + shake_y,
            ),
        )

        if combo >= 2:

            combo_text = font_medium.render(
                "COMBO x"
                + str(
                    min(combo, 5)
                ),
                True,
                (255, 220, 70),
            )

            screen.blit(
                combo_text,
                combo_text.get_rect(
                    center=(
                        SCREEN_WIDTH // 2,
                        55,
                    )
                ),
            )

        timer_value = max(
            0,
            int(
                math.ceil(
                    game_time
                )
            ),
        )

        timer_color = WHITE

        if game_time <= 10:

            pulse = (
                0.5
                + 0.5
                * math.sin(
                    total_time * 8
                )
            )

            timer_color = (
                255,
                int(
                    100
                    + 100 * pulse
                ),
                100,
            )

        timer_text = font_medium.render(
            str(timer_value),
            True,
            timer_color,
        )

        timer_rect = timer_text.get_rect(
            top=28,
            right=SCREEN_WIDTH - 35,
        )

        screen.blit(
            timer_text,
            timer_rect,
        )

        bar_width = 300
        bar_height = 10

        bar_x = (
            SCREEN_WIDTH
            - bar_width
            - 35
        )

        bar_y = 78

        pygame.draw.rect(
            screen,
            (35, 40, 65),
            (
                bar_x,
                bar_y,
                bar_width,
                bar_height,
            ),
            border_radius=5,
        )

        pygame.draw.rect(
            screen,
            timer_color,
            (
                bar_x,
                bar_y,
                int(
                    bar_width
                    * game_time
                    / GAME_DURATION
                ),
                bar_height,
            ),
            border_radius=5,
        )

    screen.blit(
        world,
        (
            shake_x,
            shake_y,
        ),
    )

    # ========================================================
    # BOMB BLAST
    # ========================================================

    if game_state == BOMB_BLAST:

        progress = clamp(
            bomb_blast_timer / 0.9,
            0.0,
            1.0
        )

        # White flash at beginning
        flash_alpha = int(
            max(
                0,
                255
                * (1.0 - progress * 2.5)
            )
        )

        if flash_alpha > 0:

            flash = pygame.Surface(
                (
                    SCREEN_WIDTH,
                    SCREEN_HEIGHT
                ),
                pygame.SRCALPHA
            )

            flash.fill(
                (
                    255,
                    255,
                    255,
                    flash_alpha
                )
            )

            screen.blit(
                flash,
                (0, 0)
            )

        # Expanding red blast ring
        blast_radius = int(
            50
            + progress * 850
        )

        ring_alpha = int(
            230
            * (1.0 - progress)
        )

        blast = pygame.Surface(
            (
                SCREEN_WIDTH,
                SCREEN_HEIGHT
            ),
            pygame.SRCALPHA
        )

        pygame.draw.circle(
            blast,
            (
                255,
                40,
                30,
                max(0, ring_alpha // 5)
            ),
            (
                int(bomb_blast_x),
                int(bomb_blast_y)
            ),
            blast_radius
        )

        pygame.draw.circle(
            blast,
            (
                255,
                80,
                40,
                ring_alpha
            ),
            (
                int(bomb_blast_x),
                int(bomb_blast_y)
            ),
            blast_radius,
            max(
                4,
                int(25 * (1.0 - progress))
            )
        )

        # Inner explosion
        inner_radius = int(
            25
            + progress * 260
        )

        pygame.draw.circle(
            blast,
            (
                255,
                180,
                60,
                int(
                    170
                    * (1.0 - progress)
                )
            ),
            (
                int(bomb_blast_x),
                int(bomb_blast_y)
            ),
            inner_radius
        )

        screen.blit(
            blast,
            (0, 0)
        )

        # Explosion warning text
        if progress < 0.65:

            warning = font_huge.render(
                "BOOM!",
                True,
                (
                    255,
                    55,
                    45
                )
            )

            warning_scale = (
                0.65
                + progress * 0.9
            )

            warning = pygame.transform.rotozoom(
                warning,
                random.uniform(-2, 2),
                warning_scale
            )

            screen.blit(
                warning,
                warning.get_rect(
                    center=(
                        int(bomb_blast_x),
                        int(bomb_blast_y)
                    )
                )
            )

    # ========================================================
    # START
    # ========================================================

    if game_state == START:

        overlay = pygame.Surface(
            (
                SCREEN_WIDTH,
                SCREEN_HEIGHT,
            ),
            pygame.SRCALPHA,
        )

        overlay.fill(
            (5, 7, 18, 150)
        )

        screen.blit(
            overlay,
            (0, 0),
        )

        pulse = (
            1.0
            + 0.04
            * math.sin(
                total_time * 2
            )
        )

        title = font_huge.render(
            "FRUIT RUSH",
            True,
            WHITE,
        )

        title = pygame.transform.rotozoom(
            title,
            0,
            pulse,
        )

        screen.blit(
            title,
            title.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    240,
                )
            ),
        )

        subtitle = font_medium.render(
            "POSE-CONTROLLED AI ARCADE",
            True,
            (130, 180, 255),
        )

        screen.blit(
            subtitle,
            subtitle.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    315,
                )
            ),
        )

        instruction = font_medium.render(
            "MOVE YOUR HAND TO PLAY",
            True,
            WHITE,
        )

        screen.blit(
            instruction,
            instruction.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    420,
                )
            ),
        )

        enter_text = font_small.render(
            "ENTER also works for testing",
            True,
            (130, 140, 170),
        )

        screen.blit(
            enter_text,
            enter_text.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    470,
                )
            ),
        )

    # ========================================================
    # GAME OVER
    # ========================================================

    elif game_state == GAME_OVER:

        overlay = pygame.Surface(
            (
                SCREEN_WIDTH,
                SCREEN_HEIGHT,
            ),
            pygame.SRCALPHA,
        )

        overlay.fill(
            (5, 5, 15, 205)
        )

        screen.blit(
            overlay,
            (0, 0),
        )

        title = font_huge.render(
            "GAME OVER",
            True,
            WHITE,
        )

        screen.blit(
            title,
            title.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    240,
                )
            ),
        )

        score_text = font_large.render(
            "SCORE  "
            + str(score),
            True,
            (255, 220, 70),
        )

        screen.blit(
            score_text,
            score_text.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    350,
                )
            ),
        )

        prompt = font_medium.render(
            "PRESS ENTER",
            True,
            WHITE,
        )

        screen.blit(
            prompt,
            prompt.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    450,
                )
            ),
        )

    # ========================================================
    # NAME ENTRY
    # ========================================================

    elif game_state == NAME_ENTRY:

        overlay = pygame.Surface(
            (
                SCREEN_WIDTH,
                SCREEN_HEIGHT,
            ),
            pygame.SRCALPHA,
        )

        overlay.fill(
            (5, 5, 15, 220)
        )

        screen.blit(
            overlay,
            (0, 0),
        )

        title = font_large.render(
            "ENTER YOUR NAME",
            True,
            WHITE,
        )

        screen.blit(
            title,
            title.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    230,
                )
            ),
        )

        box = pygame.Rect(
            SCREEN_WIDTH // 2 - 260,
            330,
            520,
            75,
        )

        pygame.draw.rect(
            screen,
            (25, 30, 55),
            box,
            border_radius=12,
        )

        pygame.draw.rect(
            screen,
            (100, 150, 255),
            box,
            3,
            border_radius=12,
        )

        name_text = font_medium.render(
            name_input + "_",
            True,
            WHITE,
        )

        screen.blit(
            name_text,
            name_text.get_rect(
                center=box.center,
            ),
        )

        prompt = font_small.render(
            "ENTER to submit",
            True,
            (150, 160, 190),
        )

        screen.blit(
            prompt,
            prompt.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    450,
                )
            ),
        )

    # ========================================================
    # LEADERBOARD
    # ========================================================

    elif game_state == LEADERBOARD:

        overlay = pygame.Surface(
            (
                SCREEN_WIDTH,
                SCREEN_HEIGHT,
            ),
            pygame.SRCALPHA,
        )

        overlay.fill(
            (5, 7, 18, 230)
        )

        screen.blit(
            overlay,
            (0, 0),
        )

        title = font_large.render(
            "LEADERBOARD",
            True,
            (255, 220, 70),
        )

        screen.blit(
            title,
            title.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    90,
                )
            ),
        )

        scores = get_top_scores(10)

        y = 165

        for index, row in enumerate(
            scores
        ):

            name, player_score, timestamp = row

            rank_text = font_medium.render(
                str(index + 1),
                True,
                (130, 150, 200),
            )

            name_text = font_medium.render(
                name,
                True,
                WHITE,
            )

            score_text = font_medium.render(
                str(player_score),
                True,
                (255, 220, 70),
            )

            screen.blit(
                rank_text,
                (280, y),
            )

            screen.blit(
                name_text,
                (370, y),
            )

            screen.blit(
                score_text,
                (850, y),
            )

            y += 43

        # Reset button
        reset_button = pygame.Rect(
            SCREEN_WIDTH // 2 - 145,
            610,
            290,
            55,
        )

        pygame.draw.rect(
            screen,
            (80, 25, 40),
            reset_button,
            border_radius=10,
        )

        pygame.draw.rect(
            screen,
            (220, 70, 90),
            reset_button,
            2,
            border_radius=10,
        )

        reset_text = font_small.render(
            "RESET LEADERBOARD",
            True,
            WHITE,
        )

        screen.blit(
            reset_text,
            reset_text.get_rect(
                center=reset_button.center,
            ),
        )

        prompt = font_small.render(
            "Press R to reset",
            True,
            (120, 130, 160),
        )

        screen.blit(
            prompt,
            prompt.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    680,
                )
            ),
        )

    # ========================================================
    # RESET CONFIRMATION
    # ========================================================

    elif game_state == RESET_CONFIRM:

        overlay = pygame.Surface(
            (
                SCREEN_WIDTH,
                SCREEN_HEIGHT,
            ),
            pygame.SRCALPHA,
        )

        overlay.fill(
            (5, 5, 15, 245)
        )

        screen.blit(
            overlay,
            (0, 0),
        )

        title = font_large.render(
            "RESET LEADERBOARD?",
            True,
            (255, 90, 100),
        )

        screen.blit(
            title,
            title.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    260,
                )
            ),
        )

        warning = font_medium.render(
            "ALL SCORES WILL BE DELETED",
            True,
            WHITE,
        )

        screen.blit(
            warning,
            warning.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    350,
                )
            ),
        )

        yes_text = font_medium.render(
            "Y  -  YES, RESET",
            True,
            (255, 100, 110),
        )

        no_text = font_medium.render(
            "N  -  CANCEL",
            True,
            (120, 200, 255),
        )

        screen.blit(
            yes_text,
            yes_text.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    440,
                )
            ),
        )

        screen.blit(
            no_text,
            no_text.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    500,
                )
            ),
        )

    pygame.display.flip()


# ============================================================
# CLEANUP
# ============================================================

pygame.quit()













