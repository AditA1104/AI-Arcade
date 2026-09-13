import pygame


def get_player_position():
    """
    Return the player's current position as (x, y).

    Currently uses the mouse as a stand-in for hand tracking.

    IMPORTANT:
    Do not read pygame.mouse anywhere else in the game.
    During integration, this function will be replaced with
    the vision module's get_player_position().
    """
    return pygame.mouse.get_pos()
