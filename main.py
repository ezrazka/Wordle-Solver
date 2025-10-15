import pickle
import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from wordle import Wordle
from Game import Game
from utils import timer

PREDEFINED_ANSWER = None

with open(os.path.join("assets", "words", "word_list.pkl"), "rb") as f:
    word_list = pickle.load(f)

if __name__ == "__main__":
    wordle = Wordle(word_list, answer=PREDEFINED_ANSWER)
    game = Game(wordle)

    with timer():
        game.start()