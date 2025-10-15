import signal
from math import log2
from .Trie import Trie

class WordleSolver:
    @staticmethod
    def get_k_optimal_guesses(word_list, grid, color_grid, word_index, chunk_size, pool, k):
        chunk = word_list[word_index:word_index+chunk_size]
        possible_answers = WordleSolver._get_possible_answers(word_list, grid, color_grid)

        entropies = pool.starmap(
            WordleSolver._get_shannon_entropy,
            [(word, possible_answers) for word in chunk]
        )
        
        possible_answers_trie = Trie()
        for answer in possible_answers:
            possible_answers_trie.insert(answer)
            
        words_and_entropies = zip(chunk, entropies)
        best_narrowing_words = [(word, entropy, possible_answers_trie.search(word)) for word, entropy in words_and_entropies]
        best_narrowing_words.sort(key=lambda x: (x[1], x[2]), reverse=True)

        best_valid_word = None
        for guess, entropy, is_valid_word in best_narrowing_words:
            if is_valid_word:
                best_valid_word = (guess, entropy, is_valid_word)
                break

        best_narrowing_words = best_narrowing_words[:k]

        return best_narrowing_words, best_valid_word
    
    @staticmethod
    def _get_possible_answers(word_list, grid, color_grid):
        possible_answers = []

        for word in word_list:
            is_possible_answer = True
            for row, color_row in zip(grid, color_grid):
                if row[0] == " ":
                    break

                grid_word = "".join(row)
                coloring = WordleSolver._get_coloring(grid_word, word)

                if coloring != color_row:
                    is_possible_answer = False
                    break
            
            if is_possible_answer:
                possible_answers.append(word)

        return possible_answers
    
    @staticmethod
    def _get_coloring(word, answer):
        counts = [0] * 26
        for char in answer:
            counts[ord(char) - ord('A')] += 1

        coloring = ["x"] * 5

        for i in range(5):
            if coloring[i] != "x":
                continue

            if word[i] == answer[i]:
                coloring[i] = "g"
                counts[ord(word[i]) - ord('A')] -= 1

        for i in range(5):
            if coloring[i] != "x":
                continue

            if counts[ord(word[i]) - ord('A')] > 0:
                coloring[i] = "y"
                counts[ord(word[i]) - ord('A')] -= 1
                
        return coloring
    
    @staticmethod
    def _get_coloring_id(coloring):
        coloring_id = 0
        exponent = 1
        for color in coloring:
            if color == "x":
                coloring_id += 0 * exponent
            elif color == "y":
                coloring_id += 1 * exponent
            elif color == "g":
                coloring_id += 2 * exponent
            else:
                raise ValueError("Invalid coloring in row.")
            exponent *= 3
        
        return coloring_id
    
    @staticmethod
    def _get_shannon_entropy(word, possible_answers):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        coloring_counts = [0] * (3 ** 5)
        for answer in possible_answers:
            coloring = WordleSolver._get_coloring(word, answer)
            coloring_id = WordleSolver._get_coloring_id(coloring)
            coloring_counts[coloring_id] += 1
        
        entropy = 0
        total_answers = len(possible_answers)
        for count in coloring_counts:
            p = count / total_answers
            if p > 0:
                entropy -= p * log2(p)
        return entropy