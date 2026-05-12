import os
import sys
import time

def restart_program():
    print("Restarting program...")
    python = sys.executable
    os.execl(python, python, *sys.argv)

if __name__ == "__main__":
    print(f"Program started with PID {os.getpid()}")
    time.sleep(2)
    restart_program()
