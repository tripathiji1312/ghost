import threading
import itertools
import time
import sys
  
class Spinner:
    def __init__(self, message="Processing"):
        self.message = message
        self.spinner = itertools.cycle(['|', '/', '-', '\\'])
        self.running = False
        self.thread = None 

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.animate)
        self.thread.start()

    def animate(self):
        while self.running:
            sys.stdout.write(f"\r{self.message} {next(self.spinner)}")
            sys.stdout.flush()
            time.sleep(0.1)

    def stop(self):
        self.running = False
        self.thread.join()
        sys.stdout.write("\rDone!          \n")

def main(): # Example usage
    spinner = Spinner("Loading")
    spinner.start()

    # Simulate long task
    time.sleep(5)

    spinner.stop()

if __name__ == "__main__":
    main()
