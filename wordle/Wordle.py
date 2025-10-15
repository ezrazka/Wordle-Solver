import random
from .colors import colorize

class Wordle:
    def __init__(self, word_list, *, answer=None):
        self._word_list = word_list
        self._answer = answer if answer else random.choice(word_list)
        self._grid = [[" "] * 5 for _ in range(6)]
        self._color_grid = [["x"] * 5 for _ in range(6)]
        self._guesses_made = 0

        self._win = False
        self._is_game_active = True

    @staticmethod
    def _require_game_active(func):
        def wrapper(self, *args, **kwargs):
            if not self._is_game_active:
                raise Exception("Game has ended.")
            return func(self, *args, **kwargs)
        return wrapper

    @property
    def word_list(self):
        return self._word_list

    @property
    def grid(self):
        return self._grid

    @property
    def color_grid(self):
        return self._color_grid
    
    @property
    def guesses_made(self):
        return self._guesses_made

    @property
    def win(self):
        return self._win
    
    @property
    def is_game_active(self):
        return self._is_game_active
    
    def display_grid(self, *, colors_only=False):
        for row, color_row in zip(self._grid, self._color_grid):
            for char, color in zip(row, color_row):
                if (colors_only):
                    print(colorize(" ", color), end="")
                else:
                    print(colorize(char, color), end="")
            print()
    
    @_require_game_active
    def is_valid_guess(self, word):
        return word in self._word_list
    
    @_require_game_active
    def guess_word(self, word):
        if not self.is_valid_guess(word):
            raise ValueError("Invalid guess word.")
        
        self._grid[self._guesses_made] = list(word)
        coloring = self._get_coloring(word)
        self._color_grid[self._guesses_made] = coloring
        self._guesses_made += 1

        if word == self._answer:
            self._win = True
            self._is_game_active = False
        elif self._guesses_made == 6:
            self._is_game_active = False
    
    @_require_game_active
    def _get_coloring(self, word):
        counts = [0] * 26
        for char in self._answer:
            counts[ord(char) - ord('A')] += 1

        coloring = ["x"] * 5

        for i in range(5):
            if coloring[i] != "x":
                continue

            if word[i] == self._answer[i]:
                coloring[i] = "g"
                counts[ord(word[i]) - ord('A')] -= 1

        for i in range(5):
            if coloring[i] != "x":
                continue

            if counts[ord(word[i]) - ord('A')] > 0:
                coloring[i] = "y"
                counts[ord(word[i]) - ord('A')] -= 1

        return coloring