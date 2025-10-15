import pygame
import signal
import threading
import queue
import os
import random
import math
from multiprocessing import Pool, cpu_count
from wordle import WordleSolver

WIDTH, HEIGHT = 800, 500
CELL_SIZE = 52
PADDING = 5
WORD_SUGGESTIONS_SIZE = 6

WHITE = (255, 255, 255)
GRAY = (58, 58, 60)
ON_GRAY = (86, 87, 88)
BORDER_GRAY = (150, 150, 150)
BLUE = (88, 196, 221)
YELLOW = (181, 159, 59)
GREEN = (83, 141, 78)
RED = (190, 60, 60)
BLACK = (0, 0, 0)

class Game:
    def __init__(self, wordle):
        self._game = wordle
        self._is_game_started = False
        self._guess_letters = []
        self._word_suggestions = []
        self._best_valid_suggestion = None
        self._suggestions_progress = 0.0
        self._grid_rects = [[None for _ in range(5)] for _ in range(6)]
        self._grid_rect_colors = [[None for _ in range(5)] for _ in range(6)]

        for row in range(6):
            for col in range(5):
                x = col * (CELL_SIZE + PADDING) + 100
                y = row * (CELL_SIZE + PADDING) + 80
                rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
                self._grid_rects[row][col] = rect
                self._grid_rect_colors[row][col] = GRAY

        self._is_game_ended = threading.Event()
        self._game_state_lock = threading.Lock()
        self._word_suggestions_lock = threading.Lock()
        self._suggestions_progress_lock = threading.Lock()
        self._suggestions_executor_pool = Pool(processes=cpu_count())
        self._suggestions_task_queue = queue.Queue()
        self._suggestions_worker_thread = threading.Thread(target=self._suggestions_worker_loop, daemon=True)
        self._suggestions_worker_thread.start()

        self._screen = None
        self._clock = None
        self._wordle_font = None
        self._text_font = None
        self._banner_message = None
        self._banner_end = None
    
    def start(self):
        if self._is_game_started:
            raise RuntimeError("Game is already running.")
        
        self._is_game_started = True

        pygame.init()
        pygame.display.set_caption("Wordle Solver")
        self._screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self._clock = pygame.time.Clock()

        wordle_font_path = os.path.join("assets", "fonts", "franklin_gothic_bold.ttf")
        text_font_path = os.path.join("assets", "fonts", "noto_sans.ttf")
        self._wordle_font = pygame.font.Font(wordle_font_path, 32)
        self._text_font = pygame.font.Font(text_font_path, 32)

        self._update_word_suggestions()

        self._run_game_loop()
        self._clean_up_resources()
    
    def _run_game_loop(self):
        running = True

        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        print("Game exit detected. Cleaning up resources...")
                        running = False
                    
                    if not self._is_game_ended.is_set():
                        self._check_for_modifier_keys(event)
                
                self._screen.fill(BLACK)

                if not self._is_game_ended.is_set():
                    self._display_game_screen()
                elif self._game.win:
                    self._display_win_screen()
                else:
                    self._display_lose_screen()
                
                pygame.display.flip()
        except KeyboardInterrupt:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            print("\nKeyboard interrupt detected. Cleaning up resources...")
            pass
    
    def _check_for_modifier_keys(self, event):
        if pygame.key.get_mods() & (pygame.KMOD_CTRL | pygame.KMOD_META | pygame.KMOD_ALT):
            return
        
        if event.type == pygame.KEYDOWN:
            if event.unicode.isalpha():
                self._type_letter(event.unicode.upper())
            elif event.key == pygame.K_BACKSPACE:
                if self._guess_letters:
                    self._delete_letter()
            elif event.key == pygame.K_RETURN:
                if len(self._guess_letters) == 5:
                    guess = "".join(self._guess_letters)
                    if not self._game.is_valid_guess(guess):
                        self._trigger_not_in_word_list_banner()
                    else:
                        self._make_guess(guess)
                else:
                    self._trigger_not_enough_letters_banner()
    
    def _type_letter(self, letter):
        with self._game_state_lock:
            guesses_made = self._game.guesses_made

        if len(self._guess_letters) == 5:
            return
        
        self._guess_letters.append(letter)

        row = guesses_made
        col = len(self._guess_letters) - 1
        self._grid_rect_colors[row][col] =ON_GRAY 

    def _delete_letter(self):
        with self._game_state_lock:
            guesses_made = self._game.guesses_made

        if len(self._guess_letters) == 0:
            return
        
        self._guess_letters.pop()

        row = guesses_made
        col = len(self._guess_letters)
        self._grid_rect_colors[row][col] = GRAY
    
    def _trigger_not_in_word_list_banner(self):
        self._banner_message = "Not in word list."
        self._banner_end = pygame.time.get_ticks() + 2000
    
    def _trigger_not_enough_letters_banner(self):
        self._banner_message = "Not enough letters."
        self._banner_end = pygame.time.get_ticks() + 2000
    
    def _make_guess(self, guess):
        with self._game_state_lock:
            self._game.guess_word(guess)
        self._guess_letters.clear()
        self._suggestions_progress = 0.0
        with self._word_suggestions_lock:
            self._best_valid_suggestion = None
            self._word_suggestions.clear()
        
        self._update_grid_rect_colors()

        with self._game_state_lock:
            guesses_made = self._game.guesses_made
        
        if self._game.win or guesses_made == 6:
            self._clean_up_resources()
        else:
            self._update_word_suggestions()
        
    def _update_grid_rect_colors(self):
        with self._game_state_lock:
            color_grid = self._game.color_grid
            guesses_made = self._game.guesses_made

        row = guesses_made - 1
        for col in range(5):
            if color_grid[row][col] == "g":
                self._grid_rect_colors[row][col] = GREEN
            elif color_grid[row][col] == "y":
                self._grid_rect_colors[row][col] = YELLOW
            else:
                self._grid_rect_colors[row][col] =ON_GRAY 
    
    def _suggestions_worker_loop(self):
        while not self._is_game_ended.is_set():
            worker = self._suggestions_task_queue.get()

            if worker is None:
                break
            
            try:
                worker()
            except Exception as e:
                print(f"Error in worker thread: {e}")
            finally:
                self._suggestions_task_queue.task_done()
    
    def _update_word_suggestions(self):
        def worker():
            with self._game_state_lock:
                grid = [row[:] for row in self._game.grid]
                color_grid = [row[:] for row in self._game.color_grid]
                thread_guesses_made = self._game.guesses_made
            
            word_list = self._game.word_list[:]
            random.shuffle(word_list)

            possible_answers = WordleSolver._get_possible_answers(word_list, grid, color_grid)

            word_index = 0
            chunk_size_constant = 8
            chunk_size = chunk_size_constant * math.ceil(len(word_list) / len(possible_answers))
            while not self._is_game_ended.is_set() and word_index < len(word_list):
                with self._game_state_lock:
                    is_still_same = (thread_guesses_made == self._game.guesses_made)
                
                if not is_still_same:
                    break

                chunk_results, chunk_best_valid_suggestion = WordleSolver.get_k_optimal_guesses(
                    word_list=word_list,
                    grid=grid,
                    color_grid=color_grid,
                    word_index=word_index,
                    chunk_size=chunk_size,
                    pool=self._suggestions_executor_pool,
                    k=WORD_SUGGESTIONS_SIZE
                )

                with self._game_state_lock:
                    is_still_same = (thread_guesses_made == self._game.guesses_made)

                if not is_still_same:
                    break

                with self._suggestions_progress_lock:
                    self._suggestions_progress = min(1.0, (word_index + chunk_size) / len(word_list))
                
                if not self._is_game_ended.is_set() and is_still_same:
                    self._merge_word_suggestions(chunk_results, chunk_best_valid_suggestion)

                word_index += chunk_size

        self._suggestions_task_queue.put(worker)

    def _merge_word_suggestions(self, new_suggestions, new_best_valid_suggestion):
        with self._word_suggestions_lock:
            new_word_suggestions = self._word_suggestions + new_suggestions
            new_word_suggestions.sort(key=lambda x: (x[1], x[2]), reverse=True)

            if self._best_valid_suggestion is None or (new_best_valid_suggestion is not None and new_best_valid_suggestion[1] > self._best_valid_suggestion[1]):
                self._best_valid_suggestion = new_best_valid_suggestion

            is_not_narrowing_and_invalid = new_word_suggestions[-1][1] == 0 and not new_word_suggestions[-1][2]
            while len(new_word_suggestions) > 0 and (len(new_word_suggestions) > WORD_SUGGESTIONS_SIZE or is_not_narrowing_and_invalid):
                new_word_suggestions.pop()

            self._word_suggestions = new_word_suggestions
    
    def _clean_up_resources(self):
        self._is_game_ended.set()
        self._suggestions_task_queue.put(None)
        self._suggestions_worker_thread.join()
        with self._word_suggestions_lock:
            self._best_valid_suggestion = None
            self._word_suggestions.clear()
        self._suggestions_executor_pool.close()
        self._suggestions_executor_pool.join()

    def _draw_cell(self, row, col):
        with self._game_state_lock:
            guesses_made = self._game.guesses_made
            grid = self._game.grid

        if row < guesses_made:
            pygame.draw.rect(self._screen, self._grid_rect_colors[row][col], self._grid_rects[row][col])
        else:
            pygame.draw.rect(self._screen, self._grid_rect_colors[row][col], self._grid_rects[row][col], width=2)

        letter = None
        if row < guesses_made:
            letter = grid[row][col]
        elif row == guesses_made and col < len(self._guess_letters):
            letter = self._guess_letters[col]
        
        if letter is not None:
            letter_surface = self._wordle_font.render(letter, True, WHITE)
            letter_rect = letter_surface.get_rect(center=self._grid_rects[row][col].center)
            self._screen.blit(letter_surface, letter_rect)

    def _draw_banner(self):
        if self._banner_message is None:
            return
        
        banner_surface = self._text_font.render(self._banner_message, True, RED)
        banner_rect = banner_surface.get_rect(center=(WIDTH // 2, HEIGHT - 40))
        self._screen.blit(banner_surface, banner_rect)

        if pygame.time.get_ticks() >= self._banner_end:
            self._banner_message = None
            self._banner_end = None
    
    def _draw_word_suggestions(self):
        title_surface = self._text_font.render("Word Suggestions", True, WHITE)
        title_rect = title_surface.get_rect(topright=(WIDTH - 65, 35))
        self._screen.blit(title_surface, title_rect)
        
        with self._word_suggestions_lock:
            if self._best_valid_suggestion is not None:
                if self._best_valid_suggestion in self._word_suggestions:
                    word_suggestions = [self._best_valid_suggestion] + [w for w in self._word_suggestions if w != self._best_valid_suggestion]
                else:
                    word_suggestions = ([self._best_valid_suggestion] + self._word_suggestions[:])[:WORD_SUGGESTIONS_SIZE]
            else:
                word_suggestions = self._word_suggestions[:]
        
        if len(word_suggestions) == 0:
            loading_text_surface = self._text_font.render("Loading...", True, WHITE)
            loading_text_rect = loading_text_surface.get_rect(topright=(WIDTH - 130, 180))
            self._screen.blit(loading_text_surface, loading_text_rect)
            return
        
        for i, (word, entropy, is_valid_word) in enumerate(word_suggestions):
            text_color = BLUE if is_valid_word else WHITE
            word_suggestion_surface = self._text_font.render(word, True, text_color)
            word_suggestion_rect = word_suggestion_surface.get_rect(topleft=(WIDTH - 355, 90 + i * 40))
            entropy_suggestion_surface = self._text_font.render(f"({entropy:.2f})", True, text_color)
            entropy_suggestion_rect = entropy_suggestion_surface.get_rect(topright=(WIDTH - 65, 90 + i * 40))
            self._screen.blit(word_suggestion_surface, word_suggestion_rect)
            self._screen.blit(entropy_suggestion_surface, entropy_suggestion_rect)
    
    def _draw_progress_bar(self):
        width, height = 300, 28
        top_left, top_right = WIDTH - width - 60, HEIGHT - height - 120
        border_width = 3
    
        pygame.draw.rect(self._screen, BORDER_GRAY, (top_left, top_right, width, height))
        pygame.draw.rect(self._screen, WHITE, (top_left, top_right, width, height), border_width)
        
        with self._suggestions_progress_lock:
            progress = self._suggestions_progress
        fill_width = int(width * progress)

        pygame.draw.rect(self._screen, BLUE, (
            top_left + border_width,
            top_right + border_width,
            fill_width - 2 * border_width,
            height - 2 * border_width
        ))

    def _display_game_screen(self):
        for row in range(6):
            for col in range(5):
                self._draw_cell(row, col)
        
        self._draw_banner()
        self._draw_word_suggestions()
        self._draw_progress_bar()

    def _display_win_screen(self):
        with self._game_state_lock:
            guesses_made = self._game.guesses_made

        title_texts = [
            "You won!",
            "It only took you",
            f"{guesses_made} guesses!"
        ]
        title_tops = [
            180,
            240,
            280
        ]
        title_surfaces = [
            self._text_font.render(text, True, WHITE)
            for text in title_texts
        ]
        title_rects = [
            surface.get_rect(center=(220, top))
            for surface, top in zip(title_surfaces, title_tops)
        ]

        for surface, rect in zip(title_surfaces, title_rects):
            self._screen.blit(surface, rect)

        for row in range(6):
            for col in range(5):
                self._grid_rects[row][col].x = col * (CELL_SIZE + PADDING) + 420
                self._grid_rects[row][col].y = row * (CELL_SIZE + PADDING) + 80
                self._draw_cell(row, col)

    def _display_lose_screen(self):
        title_texts = [
            "You lost!",
            "The correct answer",
            "was"
        ]
        title_tops = [
            150,
            210,
            240
        ]
        title_surfaces = [
            self._text_font.render(text, True, WHITE)
            for text in title_texts
        ]
        title_rects = [
            surface.get_rect(center=(220, top))
            for surface, top in zip(title_surfaces, title_tops)
        ]

        for surface, rect in zip(title_surfaces, title_rects):
            self._screen.blit(surface, rect)
        
        for col in range(5):
            row = 5

            x = 220 - ((2 - col) * (CELL_SIZE + PADDING)) - CELL_SIZE / 2
            y = 280
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(self._screen, GREEN, rect)

            letter = self._game._answer[col]
            letter_surface = self._wordle_font.render(letter, True, WHITE)
            letter_rect = letter_surface.get_rect(center=rect.center)
            self._screen.blit(letter_surface, letter_rect)

        for row in range(6):
            for col in range(5):
                self._grid_rects[row][col].x = col * (CELL_SIZE + PADDING) + 420
                self._grid_rects[row][col].y = row * (CELL_SIZE + PADDING) + 80
                self._draw_cell(row, col)