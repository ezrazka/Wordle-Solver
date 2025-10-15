import time

class timer():
    def __enter__(self):
        self.start_time = time.time()
    
    def __exit__(self, exc_type, exc_value, traceback):
        elapsed_time = time.time() - self.start_time
        print(f"Took {elapsed_time:.2f} seconds to execute.")