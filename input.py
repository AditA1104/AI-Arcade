"""
Integration boundary between the game (main.py) and player input.

This is the ONLY file that decides where player position comes from.
It now wires straight through to the live pose-tracking module
(vision.py). main.py never touches vision.py or pygame.mouse directly.

To fall back to mouse control for quick local testing without a
camera, comment out the vision import block below and uncomment the
pygame-mouse block instead.
"""

from vision import init_tracker, get_player_position, shutdown_tracker

__all__ = ["init_tracker", "get_player_position", "shutdown_tracker"]


# ---- Mouse fallback (uncomment to test without a camera) ----
# import pygame
#
# def init_tracker():
#     pass
#
# def get_player_position():
#     return pygame.mouse.get_pos()
#
# def shutdown_tracker():
#     pass
