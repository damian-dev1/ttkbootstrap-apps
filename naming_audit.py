import os
import re
import ast
import csv
from pathlib import Path
from fpdf import FPDF
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
from tkinter import filedialog, messagebox

SNAKE_CASE = re.compile(r'^[a-z_][a-z0-9_]*$')
PASCAL_CASE = re.compile(r'^[A-Z][a-zA-Z0-9]+$')
ALL_CAPS = re.compile(r'^[A-Z_][A-Z0-9_]*$')
VAGUE_NAMES = {"temp", "data", "info", "foo", "bar", "stuff", "thing", "obj"}

def check_name(name, kind):
    if name in VAGUE_NAMES:
        return f"[BAD] {kind} `{name}` is too vague"
    if kind == "variable" and not SNAKE_CASE.match(name):
        return f"[WARN] Variable `{name}` should be `snake_case`"
    if kind == "function" and not SNAKE_CASE.match(name):
        return f"[WARN] Function `{name}` should be `snake_case`"
    if kind == "class" and not PASCAL_CASE.match(name):
        return f"[WARN] Class `{name}` should be `PascalCase`"
    if kind == "constant" and not ALL_CAPS.match(name):
        return f"[WARN] Constant `{name}` should be `ALL_CAPS`"
    return None

def audit_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError as e:
            return [(file_path, 0, f"[ERROR] {e}")]
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            result = check_name(node.name, "function")
            if result:
                findings.append((file_path, node.lineno, result))
        elif isinstance(node, ast.ClassDef):
            result = check_name(node.name, "class")
            if result:
                findings.append((file_path, node.lineno, result))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    kind = "constant" if name.isupper() else "variable"
                    result = check_name(name, kind)
                    if result:
                        findings.append((file_path, node.lineno, result))
    return findings

def audit_project(directory):
    findings = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                findings.extend(audit_file(Path(root) / file))
    return findings

class AuditApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Naming Auditor")
        self.path_var = ttk.StringVar()
        self.results = []
        self.build_ui()

    def build_ui(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=BOTH, expand=True)
        path_frame = ttk.Frame(frame)
        path_frame.pack(fill=X, pady=5)
        ttk.Label(path_frame, text="Project Directory:").pack(side=LEFT, padx=5)
        ttk.Entry(path_frame, textvariable=self.path_var, width=50).pack(side=LEFT, padx=5)
        ttk.Button(path_frame, text="Browse", command=self.browse_dir, bootstyle=PRIMARY).pack(side=LEFT, padx=5)
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=X, pady=5)
        ttk.Button(btn_frame, text="Run Audit", command=self.run_audit, bootstyle=SUCCESS).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear", command=self.clear_output, bootstyle=SECONDARY).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="Export CSV", command=self.export_csv, bootstyle=INFO).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="Export PDF", command=self.export_pdf, bootstyle=WARNING).pack(side=LEFT, padx=5)
        self.output = ScrolledText(frame, wrap="word", height=25, font=("Courier New", 10))
        self.output.pack(fill=BOTH, expand=True, pady=5)

    def browse_dir(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)

    def run_audit(self):
        self.output.delete("1.0", "end")
        base_dir = self.path_var.get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showerror("Invalid Path", "Please select a valid project directory.")
            return
        self.output.insert("end", f"Running naming audit on: {base_dir}\n\n")
        self.results = audit_project(base_dir)
        if self.results:
            for file, line, msg in self.results:
                self.output.insert("end", f"{file}:{line}: {msg}\n")
            self.output.insert("end", f"\nFound {len(self.results)} issues.")
        else:
            self.output.insert("end", "No naming issues found!")

    def clear_output(self):
        self.output.delete("1.0", "end")
        self.results = []

    def export_csv(self):
        if not self.results:
            messagebox.showwarning("No Data", "No audit results to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if path:
            with open(path, "w", newline='', encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["File", "Line", "Message"])
                writer.writerows(self.results)
            messagebox.showinfo("Exported", f"CSV report saved to:\n{path}")

    def export_pdf(self):
        if not self.results:
            messagebox.showwarning("No Data", "No audit results to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if path:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=10)
            pdf.add_page()
            pdf.set_font("Courier", size=10)
            pdf.multi_cell(0, 5, f"Python Naming Audit Report\n\n")
            for file, line, msg in self.results:
                pdf.multi_cell(0, 5, f"{file}:{line}: {msg}")
            pdf.output(path)
            messagebox.showinfo("Exported", f"PDF report saved to:\n{path}")

def launch_gui():
    app = ttk.Window(themename="darkly", title="Python Naming Audit", size=(900, 650))
    AuditApp(app)
    app.mainloop()

if __name__ == "__main__":
    launch_gui()
