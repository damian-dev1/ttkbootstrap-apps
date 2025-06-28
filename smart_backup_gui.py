import os
import shutil
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox, scrolledtext, END

class BackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Backup Tool")
        self.csv_path = ttk.StringVar()
        self.backup_path = ttk.StringVar(value="C:/Backups")
        self.ext_filter = ttk.StringVar(value=".py,.vba,.md,.docx,.xlsx,.pdf,.ps1")
        self.setup_ui()

    def setup_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=BOTH, expand=True)

        ttk.Label(frm, text="CSV File:").grid(row=0, column=0, sticky=W)
        ttk.Entry(frm, textvariable=self.csv_path, width=60).grid(row=0, column=1)
        ttk.Button(frm, text="Browse", command=self.browse_csv).grid(row=0, column=2)

        ttk.Label(frm, text="Backup Folder:").grid(row=1, column=0, sticky=W)
        ttk.Entry(frm, textvariable=self.backup_path, width=60).grid(row=1, column=1)
        ttk.Button(frm, text="Browse", command=self.browse_folder).grid(row=1, column=2)

        ttk.Label(frm, text="Extensions to include (comma-separated):").grid(row=2, column=0, columnspan=2, sticky=W)
        ttk.Entry(frm, textvariable=self.ext_filter, width=60).grid(row=3, column=0, columnspan=2, sticky=W)

        ttk.Button(frm, text="Preview Backup", bootstyle=INFO, command=self.preview_backup).grid(row=4, column=0, pady=10)
        ttk.Button(frm, text="Run Backup", bootstyle=SUCCESS, command=self.run_backup).grid(row=4, column=1, pady=10, sticky=E)
        ttk.Button(frm, text="Exit", bootstyle=DANGER, command=self.root.quit).grid(row=4, column=2, pady=10)

        self.log_output = scrolledtext.ScrolledText(frm, height=20)
        self.log_output.grid(row=5, column=0, columnspan=3, sticky=NSEW)
        frm.rowconfigure(5, weight=1)
        frm.columnconfigure(1, weight=1)

    def browse_csv(self):
        file = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if file:
            self.csv_path.set(file)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.backup_path.set(folder)

    def log(self, msg):
        self.log_output.insert(END, msg + '\n')
        self.log_output.see(END)

    def load_csv_and_filter(self):
        try:
            csv_file = Path(self.csv_path.get())
            df = pd.read_csv(csv_file)

            if 'file_path' not in df.columns:
                if {'Path', 'Name'}.issubset(df.columns):
                    df['file_path'] = df.apply(
                        lambda row: os.path.join(str(row['Path']).strip(), str(row['Name']).strip()), axis=1)
                    self.log("🛠 'file_path' column generated from 'Path' + 'Name'")
                else:
                    raise ValueError("CSV must contain either 'file_path' or both 'Path' and 'Name' columns.")

            exts = {e.strip().lower() for e in self.ext_filter.get().split(',') if e.strip()}
            df['file_path'] = df['file_path'].astype(str).str.strip()
            df['valid'] = df['file_path'].apply(lambda f: Path(f).exists() and Path(f).suffix.lower() in exts)
            return df[df['valid']].copy(), exts

        except Exception as e:
            self.log(f"❌ Error loading CSV: {e}")
            return None, None

    def preview_backup(self):
        self.log_output.delete(1.0, END)
        df, _ = self.load_csv_and_filter()
        if df is None or df.empty:
            self.log("⚠️ No valid files found.")
            return

        total_files = len(df)
        total_size = sum(Path(p).stat().st_size for p in df['file_path'])

        size_mb = total_size / (1024 * 1024)
        self.log(f"🔍 Preview:")
        self.log(f"🧾 Files matched: {total_files}")
        self.log(f"💾 Estimated total size: {size_mb:.2f} MB")

    def run_backup(self):
        self.log_output.delete(1.0, END)

        backup_root = Path(self.backup_path.get())
        if not backup_root.exists():
            messagebox.showerror("Error", "Invalid Backup path.")
            return

        df, _ = self.load_csv_and_filter()
        if df is None or df.empty:
            self.log("⚠️ No valid files to back up.")
            return

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"python-files-{now}"
        backup_folder = backup_root / backup_name
        zip_path = backup_root / f"{backup_name}.zip"
        backup_folder.mkdir(parents=True, exist_ok=True)

        copied = skipped = failed = 0

        for _, row in df.iterrows():
            try:
                src = Path(row['file_path'])
                rel_path = src.drive + src.as_posix()[2:]
                rel = Path(rel_path).relative_to(Path(src.drive + "/"))
                dest = backup_folder / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                copied += 1
                self.log(f"✅ Copied: {src}")
            except PermissionError as pe:
                failed += 1
                self.log(f"🔒 Permission denied: {src} => {pe}")
            except Exception as e:
                failed += 1
                self.log(f"❌ Error copying {src}: {e}")

        try:
            shutil.make_archive(str(zip_path).replace('.zip', ''), 'zip', backup_folder)
            self.log(f"📦 ZIP created: {zip_path}")
        except Exception as e:
            self.log(f"❌ ZIP creation failed: {e}")

        self.log("--- Summary ---")
        self.log(f"✅ Copied: {copied}")
        self.log(f"⚠️ Skipped: {len(df) - copied}")
        self.log(f"❌ Failed: {failed}")

if __name__ == '__main__':
    app = ttk.Window(themename="darkly", size=(950, 700))
    BackupApp(app)
    app.mainloop()
