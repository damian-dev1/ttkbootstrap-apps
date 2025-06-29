import pathlib
import threading
import time
from datetime import datetime
from io import StringIO
from tkinter import filedialog

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class DirectoryTree:
    def __init__(self, startpath, ignore_hidden=True, max_depth=None, exclude_folders=None):
        self.startpath = pathlib.Path(startpath).resolve()
        self.ignore_hidden = ignore_hidden
        self.max_depth = max_depth
        self.exclude_folders = exclude_folders or []
        self._validate_startpath()

    def _validate_startpath(self):
        if not self.startpath.exists():
            raise FileNotFoundError(f"Path '{self.startpath}' does not exist.")
        if not self.startpath.is_dir():
            raise NotADirectoryError(f"'{self.startpath}' is not a directory.")

    def _should_include(self, item):
        if self.ignore_hidden and item.name.startswith('.'):
            return False
        if item.name in self.exclude_folders:
            return False
        return True

    def _save_tree(self, path, file, indent="", depth=0):
        if self.max_depth is not None and depth >= self.max_depth:
            return
        items = sorted((i for i in path.iterdir() if self._should_include(i)), key=lambda x: x.name.lower())
        for index, item in enumerate(items):
            prefix = "└── " if index == len(items) - 1 else "├── "
            file.write(indent + prefix + item.name + "\n")
            if item.is_dir():
                new_indent = indent + ("    " if index == len(items) - 1 else "│   ")
                self._save_tree(item, file, new_indent, depth + 1)


class DirectoryChangeHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_any_event(self, event):
        self.callback()


class DirectoryTreeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📁 Directory Tree Viewer")
        self.style = ttk.Style("litera")

        self.tab_control = ttk.Notebook(self.root)
        self.tree_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tree_tab, text="📁 Tree View")
        self.tab_control.pack(fill=BOTH, expand=True)

        self.build_tree_tab()
        self.init_tree_and_observer()

    def build_tree_tab(self):
        control_frame = ttk.Frame(self.tree_tab, padding=10)
        control_frame.pack(fill=X)

        ttk.Label(control_frame, text="Start Path:").grid(row=0, column=0, sticky=W, padx=5)
        self.path_var = ttk.StringVar(value=".")
        ttk.Entry(control_frame, textvariable=self.path_var, width=40).grid(row=0, column=1, padx=5)
        ttk.Button(control_frame, text="Browse", command=self.browse_folder).grid(row=0, column=2, padx=5)

        self.ignore_hidden_var = ttk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Ignore Hidden", variable=self.ignore_hidden_var).grid(row=1, column=0, sticky=W, padx=5, pady=5)

        ttk.Label(control_frame, text="Max Depth:").grid(row=1, column=1, sticky=E)
        self.depth_var = ttk.IntVar(value=3)
        ttk.Spinbox(control_frame, from_=1, to=20, textvariable=self.depth_var, width=5).grid(row=1, column=2, padx=5, sticky=W)

        ttk.Label(control_frame, text="Exclude (comma-separated):").grid(row=2, column=0, sticky=W, padx=5)
        self.exclude_var = ttk.StringVar(value="__pycache__,node_modules,output")
        ttk.Entry(control_frame, textvariable=self.exclude_var, width=40).grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky=W)

        ttk.Button(control_frame, text="🔄 Refresh Tree", command=self.refresh_tree_manual, bootstyle=INFO).grid(row=3, column=0, pady=10)
        ttk.Button(control_frame, text="💾 Export Tree", command=self.export_tree_to_file, bootstyle=PRIMARY).grid(row=3, column=1, pady=10)

        self.tree_output = ScrolledText(self.tree_tab, wrap="word", font=("Courier New", 10))
        self.tree_output.pack(fill=BOTH, expand=True, padx=10, pady=10)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
            self.refresh_tree_manual()

    def init_tree_and_observer(self):
        self.update_tree_instance()
        self.render_tree()
        self.observer = Observer()
        self.event_handler = DirectoryChangeHandler(self.on_fs_change)
        self.observer.schedule(self.event_handler, str(self.tree.startpath), recursive=True)
        self.observer.start()

    def update_tree_instance(self):
        path = self.path_var.get().strip()
        max_depth = self.depth_var.get()
        exclude_list = [x.strip() for x in self.exclude_var.get().split(",") if x.strip()]

        self.tree = DirectoryTree(
            startpath=path,
            ignore_hidden=self.ignore_hidden_var.get(),
            max_depth=max_depth,
            exclude_folders=exclude_list
        )

    def refresh_tree_manual(self):
        self.update_tree_instance()
        self.render_tree()

    def render_tree(self):
        buffer = StringIO()
        buffer.write(f"Directory tree for: {self.tree.startpath}\n")
        self.tree._save_tree(self.tree.startpath, buffer)
        self.tree_output.delete("1.0", "end")
        self.tree_output.insert("end", buffer.getvalue())

    def export_tree_to_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")],
            initialfile=f"directory_tree_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Directory tree for: {self.tree.startpath}\n")
                self.tree._save_tree(self.tree.startpath, f)

    def on_fs_change(self):
        def refresh():
            time.sleep(0.5)
            self.render_tree()
        threading.Thread(target=refresh, daemon=True).start()

    def on_close(self):
        if hasattr(self, 'observer'):
            self.observer.stop()
            self.observer.join()
        self.root.destroy()


def launch_gui():
    app = ttk.Window(themename="cyborg")
    gui = DirectoryTreeApp(app)
    app.protocol("WM_DELETE_WINDOW", gui.on_close)
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
