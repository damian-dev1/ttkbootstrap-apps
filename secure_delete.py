import os
import psutil
import threading
import logging
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def secure_delete(file_path, passes=3):
    if os.path.exists(file_path):
        try:
            file_size = os.path.getsize(file_path)
            with open(file_path, "wb") as f:
                for _ in range(passes):
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            os.remove(file_path)
            logging.info(f"Securely deleted: {file_path}")
        except Exception as e:
            logging.error(f"Secure delete failed: {e}")
    else:
        logging.warning(f"File not found: {file_path}")

def terminate_related_processes(file_path):
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            for f in proc.open_files():
                if f.path == file_path:
                    proc.terminate()
                    proc.wait()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass

class DeleteManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure File & Folder Deletion")
        self.root.geometry("600x500")
        self.path = None
        self.secure = ttk.BooleanVar(value=True)
        self.interval = ttk.IntVar(value=10)
        self.task = None
        self.build_ui()

    def build_ui(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=ttk.BOTH, expand=True)

        ttk.Label(frame, text="Secure Deletion Tool", font=("Segoe UI", 18, "bold")).pack(pady=10)

        path_frame = ttk.Frame(frame)
        path_frame.pack(fill=ttk.X, pady=10)
        self.path_label = ttk.Label(path_frame, text="No file/folder selected", anchor="w", width=60)
        self.path_label.pack(side=ttk.LEFT, padx=(0, 10))
        ttk.Button(path_frame, text="Select File", command=self.select_file).pack(side=ttk.LEFT, padx=2)
        ttk.Button(path_frame, text="Select Folder", command=self.select_folder).pack(side=ttk.LEFT, padx=2)

        ttk.Checkbutton(frame, text="Enable Secure Delete", variable=self.secure).pack(pady=10)

        interval_frame = ttk.Frame(frame)
        interval_frame.pack(pady=5)
        ttk.Label(interval_frame, text="Auto-Delete Interval (seconds):").pack(side=ttk.LEFT, padx=5)
        ttk.Entry(interval_frame, textvariable=self.interval, width=10).pack(side=ttk.LEFT)

        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=15)
        ttk.Button(button_frame, text="Delete Now", command=self.delete_now, bootstyle=DANGER).pack(side=ttk.LEFT, padx=10)
        ttk.Button(button_frame, text="Start Auto-Deletion", command=self.start_schedule, bootstyle=SUCCESS).pack(side=ttk.LEFT, padx=10)
        ttk.Button(button_frame, text="Stop Auto-Deletion", command=self.stop_schedule, bootstyle=WARNING).pack(side=ttk.LEFT, padx=10)

        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=200)
        self.progress.pack(pady=20)

        self.status_label = ttk.Label(frame, text="Status: Idle", font=("Segoe UI", 10))
        self.status_label.pack()

    def select_file(self):
        path = filedialog.askopenfilename(title="Select a File")
        if path:
            self.path = path
            self.path_label.config(text=path)

    def select_folder(self):
        path = filedialog.askdirectory(title="Select a Folder")
        if path:
            self.path = path
            self.path_label.config(text=path)

    def delete_now(self):
        if not self.path or os.path.isdir(self.path):
            messagebox.showerror("Invalid", "Select a valid file for deletion.")
            return
        try:
            terminate_related_processes(self.path)
            if self.secure.get():
                secure_delete(self.path)
            else:
                os.remove(self.path)
            self.status_label.config(text="Status: File deleted")
            messagebox.showinfo("Success", "File deleted successfully.")
        except Exception as e:
            self.status_label.config(text=f"Error: {e}")
            messagebox.showerror("Error", str(e))

    def start_schedule(self):
        if not self.path or not os.path.isdir(self.path):
            messagebox.showerror("Invalid", "Select a valid folder for scheduled deletion.")
            return
        self.progress.start()
        self.status_label.config(text="Status: Auto-deletion running")
        self.schedule_next()

    def stop_schedule(self):
        if self.task:
            self.task.cancel()
            self.task = None
            self.progress.stop()
            self.status_label.config(text="Status: Auto-deletion stopped")
            messagebox.showinfo("Stopped", "Auto-deletion stopped.")

    def schedule_next(self):
        self.task = threading.Timer(self.interval.get(), self.delete_folder_contents)
        self.task.start()

    def delete_folder_contents(self):
        try:
            for f in os.listdir(self.path):
                fp = os.path.join(self.path, f)
                if os.path.isfile(fp):
                    terminate_related_processes(fp)
                    if self.secure.get():
                        secure_delete(fp)
                    else:
                        os.remove(fp)
            self.status_label.config(text="Status: Folder cleaned")
        except Exception as e:
            logging.error(e)
            self.status_label.config(text=f"Error: {e}")
        finally:
            self.schedule_next()

def launch():
    app = ttk.Window(themename="darkly")
    DeleteManagerApp(app)
    app.mainloop()

if __name__ == "__main__":
    launch()
