from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import time
import os

class ReloadHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.run_script()

    def run_script(self):
        if self.process:
            self.process.terminate()
        self.process = subprocess.Popen(["python", "main.py"])

    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            print(f"{event.src_path} diubah, reload main.py...")
            self.run_script()

if __name__ == "__main__":
    path = os.getcwd()
    event_handler = ReloadHandler()
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=True)
    observer.start()
    print("Watcher aktif. Ubah file .py untuk restart main.py")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    observer.join()
