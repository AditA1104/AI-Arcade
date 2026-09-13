import pygame
from pathlib import Path
import math


ASSET_DIR = Path(__file__).parent / "fruit_assets" / "game"

FRUIT_FILES = {
    "apple": "apple.png",
    "orange": "orange.png",
    "banana": "banana.png",
    "pineapple": "pineapple.png",
    "watermelon": "watermelon.png",
}

HALF_FILES = {
    "apple": "half_apple.png",
    "orange": "half_orange.png",
    "pineapple": "half_pineapple.png",
    "watermelon": "half_watermelon.png",
}

_fruit_cache = {}
_half_cache = {}


def load_fruit(fruit_type):
    if fruit_type in _fruit_cache:
        return _fruit_cache[fruit_type]

    filename = FRUIT_FILES.get(fruit_type)

    if filename is None:
        return None

    path = ASSET_DIR / filename

    if not path.exists():
        print(f"Missing fruit asset: {path}")
        return None

    image = pygame.image.load(str(path)).convert_alpha()
    _fruit_cache[fruit_type] = image

    return image


def load_half_fruit(fruit_type):
    if fruit_type in _half_cache:
        return _half_cache[fruit_type]

    filename = HALF_FILES.get(fruit_type)

    if filename is None:
        return None

    path = ASSET_DIR / filename

    if not path.exists():
        print(f"Missing half-fruit asset: {path}")
        return None

    image = pygame.image.load(str(path)).convert_alpha()
    _half_cache[fruit_type] = image

    return image


def scale_fruit(image, fruit_type, size):
    """
    Scale each fruit independently so the visual sizes look consistent.

    size is the base fruit size used by main.py.
    """

    # Target dimensions as percentages of the base size.
    dimensions = {
        "apple": (0.58, 0.58),
        "orange": (0.48, 0.58),
        "banana": (1.05, 0.52),
        "pineapple": (0.58, 1.30),
        "watermelon": (0.88, 0.88),
    }

    target_w, target_h = dimensions.get(
        fruit_type,
        (0.75, 0.75)
    )

    width = max(1, int(size * target_w))
    height = max(1, int(size * target_h))

    return pygame.transform.smoothscale(
        image,
        (width, height)
    )


def make_custom_fruit_sprite(fruit_type, size=96):
    image = load_fruit(fruit_type)

    if image is None:
        return make_fruit_sprite(fruit_type, size)

    return scale_fruit(image, fruit_type, size)


def make_fruit_sprite(fruit_type, size=96):
    """
    Fallback sprite.
    Normally the real PNG assets are used.
    """

    surface = pygame.Surface(
        (size, size),
        pygame.SRCALPHA
    )

    center = size // 2
    radius = int(size * 0.32)

    if fruit_type == "apple":

        pygame.draw.circle(
            surface,
            (220, 40, 50),
            (center, center + 4),
            radius
        )

    elif fruit_type == "orange":

        pygame.draw.circle(
            surface,
            (245, 135, 25),
            (center, center + 4),
            radius
        )

    elif fruit_type == "banana":

        pygame.draw.arc(
            surface,
            (245, 210, 50),
            (
                center - radius,
                center - radius,
                radius * 2,
                radius * 2
            ),
            math.radians(200),
            math.radians(340),
            max(8, size // 10)
        )

    elif fruit_type == "pineapple":

        pygame.draw.ellipse(
            surface,
            (225, 165, 35),
            (
                center - int(size * 0.22),
                center - int(size * 0.40),
                int(size * 0.44),
                int(size * 0.72)
            )
        )

    elif fruit_type == "watermelon":

        pygame.draw.circle(
            surface,
            (45, 190, 85),
            (center, center),
            int(size * 0.36)
        )

    else:

        pygame.draw.circle(
            surface,
            (230, 180, 40),
            (center, center),
            radius
        )

    return surface


def make_half_fruit_sprite(fruit_type, size=96):
    image = load_half_fruit(fruit_type)

    if image is None:
        return None

    # Half fruits use a slightly smaller target.
    target_size = int(size * 0.72)

    return scale_fruit(
        image,
        fruit_type,
        target_size
    )


def make_bomb_sprite(size=96, time_value=0.0):

    surface = pygame.Surface(
        (size, size),
        pygame.SRCALPHA
    )

    center = size // 2

    # Bomb body radius.
    radius = int(size * 0.36)

    body_center = (
        center,
        center + int(size * 0.05)
    )

    # Outer dark edge.
    pygame.draw.circle(
        surface,
        (5, 5, 8),
        body_center,
        radius
    )

    # Red warning ring.
    pygame.draw.circle(
        surface,
        (220, 35, 40),
        body_center,
        radius + 3,
        max(2, size // 22)
    )

    # -------------------------------------------------
    # Smaller X.
    # It stays comfortably inside the bomb body.
    # -------------------------------------------------

    x_offset = int(size * 0.18)

    x_width = max(
        4,
        int(size * 0.085)
    )

    x_center_y = center + int(size * 0.05)

    pygame.draw.line(
        surface,
        (235, 35, 45),
        (
            center - x_offset,
            x_center_y - x_offset
        ),
        (
            center + x_offset,
            x_center_y + x_offset
        ),
        x_width
    )

    pygame.draw.line(
        surface,
        (235, 35, 45),
        (
            center + x_offset,
            x_center_y - x_offset
        ),
        (
            center - x_offset,
            x_center_y + x_offset
        ),
        x_width
    )

    # Fuse.
    fuse_start = (
        center + int(radius * 0.42),
        center - int(radius * 0.75)
    )

    fuse_end = (
        center + int(radius * 0.82),
        center - int(radius * 1.10)
    )

    pygame.draw.line(
        surface,
        (180, 130, 65),
        fuse_start,
        fuse_end,
        max(3, size // 22)
    )

    # Animated spark.
    pulse = (
        0.5
        + 0.5 * math.sin(time_value * 18)
    )

    spark_radius = max(
        3,
        int(size * (0.055 + pulse * 0.035))
    )

    pygame.draw.circle(
        surface,
        (255, 220, 80),
        fuse_end,
        spark_radius
    )

    pygame.draw.circle(
        surface,
        (255, 245, 180),
        fuse_end,
        max(
            1,
            spark_radius // 2
        )
    )

    return surface









