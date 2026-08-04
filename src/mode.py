from enum import Enum


# Режимы работы приложения: человек, графический агент и RL-агент.
class Mode(Enum):
    HUMAN = "This mode lets you play the game yourself."
    GRAPH = "This mode lets an AI play the game based on graph algorithms."
    RL = "This mode lets an AI play the game based on reinforcement learning."
