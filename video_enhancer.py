import os
import shutil
import time
import datetime
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext
from tkinter import LEFT, RIGHT, N, S, E, W, NSEW, EW, X, BOTH, DISABLED, NORMAL, EXTENDED
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pathlib import Path

class Profile:
    def __init__(self, name, qp, codec, resolution):
        self.name = name
        self.qp = qp
        self.codec = codec
        self.resolution = resolution

    def apply(self, app):
        app.qp.set(self.qp)
        app.codec_var.set(self.codec)
        app.scale_var.set(self.resolution)

class FFmpegBatchEnhancerGUI:
    THEMES = ["darkly", "solar", "superhero", "cyborg", "vapor", "morph", "minty", "flatly", "pulse", "litera", "sandstone"]

    def __init__(self, master):
        self.master = master
        self.style = master.style
        self.master.title("🎬 GPU Batch Video Enhancer (FFmpeg + NVENC)")
        self.master.geometry("526x925")
        self.master.resizable(True, True)

        self.profiles = {
            "Custom": None,
            "High Quality": Profile("High Quality", 18, "hevc_nvenc", "3840x2160"),
            "Balanced": Profile("Balanced", 22, "h264_nvenc", "1920x1080"),
            "Web 1080p": Profile("Web 1080p", 23, "h264_nvenc", "1920x1080"),
            "Web 720p": Profile("Web 720p", 24, "h264_nvenc", "1280x720"),
            "Archival": Profile("Archival", 17, "hevc_nvenc", "Original"),
        }

        self.video_files = []
        self.output_dir = tk.StringVar(value=str(Path.home() / "Videos" / "Enhanced"))
        self.qp = tk.IntVar(value=22)
        self.scale_var = tk.StringVar(value="1920x1080")
        self.format_var = tk.StringVar(value="mp4")
        self.codec_var = tk.StringVar(value="h264_nvenc")
        self.hw_decode = tk.BooleanVar(value=True)
        self.audio_passthrough = tk.BooleanVar(value=False)
        self.monitor_gpu = tk.BooleanVar(value=True)
        self.profile_var = tk.StringVar(value="Custom")
        self.status_text = tk.StringVar()
        self.theme_var = tk.StringVar(value=self.style.theme.name)

        self.is_processing = False
        self.cancel_requested = False
        self.pause_requested = False
        self.gpu_monitor_active = False
        
        self.widgets_to_disable = []

        self.setup_gui()
        self._check_dependencies()
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _check_dependencies(self):
        if not shutil.which("ffmpeg"):
            self.log("FFmpeg not found in system PATH. Please install FFmpeg and add it to your PATH.", "red")
        if not shutil.which("nvidia-smi"):
            self.log("nvidia-smi not found. GPU usage monitoring will be disabled.", "orange")
            self.monitor_gpu.set(False)

    def setup_gui(self):
        main_frame = ttk.Frame(self.master, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(header_frame, text="Theme:", bootstyle=PRIMARY).pack(side=LEFT, padx=(0, 5))
        self.theme_combobox = ttk.Combobox(header_frame, textvariable=self.theme_var, values=self.THEMES, state="readonly", width=12)
        self.theme_combobox.pack(side=LEFT, padx=5)
        self.theme_combobox.bind("<<ComboboxSelected>>", self._change_theme)
        
        header_frame.columnconfigure(0, weight=1)
        
        exit_button = ttk.Button(header_frame, text="Exit Application", command=self.on_closing, bootstyle=(DANGER, OUTLINE), width=15)
        exit_button.pack(side=RIGHT, padx=5)

        frm_top = ttk.LabelFrame(main_frame, text="File Selection", bootstyle=INFO)
        frm_top.pack(fill=X, pady=10)

        button_frame = ttk.Frame(frm_top)
        button_frame.grid(row=0, column=0, columnspan=3, pady=5, sticky=W)

        self.add_button = ttk.Button(button_frame, text="➕ Add Videos", command=self.add_files, bootstyle=SUCCESS)
        self.add_button.pack(side=LEFT, padx=5, pady=5)
        self.remove_button = ttk.Button(button_frame, text="🗑 Remove Selected", command=self.remove_selected, bootstyle=DANGER)
        self.remove_button.pack(side=LEFT, padx=5, pady=5)
        self.output_button = ttk.Button(button_frame, text="📁 Select Output Folder", command=self.select_output_dir, bootstyle=INFO)
        self.output_button.pack(side=LEFT, padx=5, pady=5)

        self.output_entry = ttk.Entry(frm_top, textvariable=self.output_dir)
        self.output_entry.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=EW)

        self.listbox = tk.Listbox(frm_top, height=8, selectmode=EXTENDED)
        self.listbox.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=NSEW)
        frm_top.grid_rowconfigure(2, weight=1)
        frm_top.grid_columnconfigure(0, weight=1)

        frm_opts = ttk.LabelFrame(main_frame, text="Encoding Settings", bootstyle=INFO)
        frm_opts.pack(fill=X, pady=10)

        ttk.Label(frm_opts, text="🎯 Preset Profile:", bootstyle=PRIMARY).grid(row=0, column=0, padx=5, pady=5, sticky=W)
        self.profile_combobox = ttk.Combobox(frm_opts, textvariable=self.profile_var, values=list(self.profiles.keys()), state="readonly", width=20, bootstyle=INFO)
        self.profile_combobox.grid(row=0, column=1, padx=5, pady=5, sticky=W)
        self.profile_var.trace_add("write", self.apply_preset)

        ttk.Label(frm_opts, text="🎥 Codec:", bootstyle=PRIMARY).grid(row=0, column=2, padx=5, pady=5, sticky=W)
        self.codec_combobox = ttk.Combobox(frm_opts, textvariable=self.codec_var, values=["h264_nvenc", "hevc_nvenc"], state="readonly", width=15, bootstyle=INFO)
        self.codec_combobox.grid(row=0, column=3, padx=5, pady=5, sticky=W)

        ttk.Label(frm_opts, text="📁 Output Format:", bootstyle=PRIMARY).grid(row=1, column=0, padx=5, pady=5, sticky=W)
        self.format_combobox = ttk.Combobox(frm_opts, textvariable=self.format_var, values=["mp4", "mkv"], state="readonly", width=10, bootstyle=INFO)
        self.format_combobox.grid(row=1, column=1, padx=5, pady=5, sticky=W)

        ttk.Label(frm_opts, text="🖼 Resolution:", bootstyle=PRIMARY).grid(row=1, column=2, padx=5, pady=5, sticky=W)
        self.scale_combobox = ttk.Combobox(frm_opts, textvariable=self.scale_var, values=["Original", "3840x2160", "2560x1440", "1920x1080", "1280x720"], state="readonly", width=15, bootstyle=INFO)
        self.scale_combobox.grid(row=1, column=3, padx=5, pady=5, sticky=W)
        
        ttk.Label(frm_opts, text="🔧 QP (Quality, 0-51):", bootstyle=PRIMARY).grid(row=2, column=0, padx=5, pady=5, sticky=W)
        self.qp_spinbox = ttk.Spinbox(frm_opts, from_=0, to=51, textvariable=self.qp, width=5, bootstyle=INFO)
        self.qp_spinbox.grid(row=2, column=1, padx=5, pady=5, sticky=W)

        self.hw_decode_check = ttk.Checkbutton(frm_opts, text="Enable NVDEC Hardware Decode", variable=self.hw_decode, bootstyle="round-toggle")
        self.hw_decode_check.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=W)
        self.audio_passthrough_check = ttk.Checkbutton(frm_opts, text="Copy original audio (Passthrough)", variable=self.audio_passthrough, bootstyle="round-toggle")
        self.audio_passthrough_check.grid(row=3, column=2, columnspan=2, padx=5, pady=5, sticky=W)
        self.monitor_gpu_check = ttk.Checkbutton(frm_opts, text="Show GPU Usage (requires nvidia-smi)", variable=self.monitor_gpu, bootstyle="round-toggle")
        self.monitor_gpu_check.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky=W)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        self.start_button = ttk.Button(btn_frame, text="🚀 Start Encoding", command=self.start_threaded_process, width=20, bootstyle=SUCCESS)
        self.start_button.grid(row=0, column=0, padx=10)
        self.pause_button = ttk.Button(btn_frame, text="⏸ Pause", command=self.request_pause, width=10, bootstyle=WARNING, state=DISABLED)
        self.pause_button.grid(row=0, column=1, padx=5)
        self.resume_button = ttk.Button(btn_frame, text="▶ Resume", command=self.request_resume, width=10, bootstyle=INFO, state=DISABLED)
        self.resume_button.grid(row=0, column=2, padx=5)
        self.cancel_button = ttk.Button(btn_frame, text="❌ Cancel", command=self.request_cancel, width=10, bootstyle=DANGER, state=DISABLED)
        self.cancel_button.grid(row=0, column=3, padx=5)

        self.widgets_to_disable.extend([
            self.add_button, self.remove_button, self.output_button, self.output_entry,
            self.profile_combobox, self.codec_combobox, self.format_combobox,
            self.scale_combobox, self.qp_spinbox, self.hw_decode_check,
            self.audio_passthrough_check, self.monitor_gpu_check, self.theme_combobox
        ])

        paned_window = ttk.PanedWindow(main_frame, orient=VERTICAL)
        paned_window.pack(fill=BOTH, expand=True, pady=5)
        
        log_frame = ttk.LabelFrame(paned_window, text="Processing Log", bootstyle=PRIMARY)
        self.log_output = scrolledtext.ScrolledText(log_frame, wrap="word", height=10, font=("TkDefaultFont", 10))
        self.log_output.pack(padx=5, pady=5, fill=BOTH, expand=True)
        paned_window.add(log_frame, weight=3)

        gpu_frame = ttk.LabelFrame(paned_window, text="GPU Usage Monitor", bootstyle=PRIMARY)
        self.gpu_output = scrolledtext.ScrolledText(gpu_frame, wrap="word", height=4, font=("TkDefaultFont", 9))
        self.gpu_output.pack(padx=5, pady=5, fill=BOTH, expand=True)
        paned_window.add(gpu_frame, weight=1)

        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=X, side=BOTTOM)
        self.status_label = ttk.Label(status_frame, textvariable=self.status_text, anchor=W)
        self.status_label.pack(fill=X, padx=5, pady=2)
        
        self.log("Application started. Ready for video processing.", "blue")
        Path(self.output_dir.get()).mkdir(parents=True, exist_ok=True)
        self._update_status("Ready", "info")

    def _change_theme(self, event=None):
        selected_theme = self.theme_var.get()
        self.style.theme_use(selected_theme)
        self._update_status(f"Theme changed to {selected_theme}", "info")

    def apply_preset(self, *args):
        profile_name = self.profile_var.get()
        profile = self.profiles.get(profile_name)
        if profile:
            profile.apply(self)
            self.log(f"Applied '{profile_name}' preset.", "green")

    def log(self, msg, color="default"):
        timestamp = time.strftime("[%H:%M:%S]")
        self.log_output.configure(state=NORMAL)
        
        tag_map = {
            "green": "success", "red": "danger", "blue": "info", "orange": "warning"
        }
        bootstyle_color = tag_map.get(color, color)
        
        if bootstyle_color in self.style.colors:
            self.log_output.tag_config(color, foreground=self.style.colors.get(bootstyle_color))
        
        self.log_output.insert(tk.END, f"{timestamp} {msg}\n", color)
        self.log_output.see(tk.END)
        self.log_output.configure(state=DISABLED)
        self.master.update_idletasks()

    def update_gpu_log(self, msg):
        self.gpu_output.configure(state=NORMAL)
        self.gpu_output.delete("1.0", tk.END)
        self.gpu_output.insert(tk.END, msg)
        self.gpu_output.configure(state=DISABLED)
        self.master.update_idletasks()

    def _update_status(self, text, bootstyle="default"):
        self.status_text.set(text)
        self.status_label.configure(bootstyle=bootstyle)

    def monitor_gpu_usage(self):
        if not shutil.which("nvidia-smi"):
            self.update_gpu_log("nvidia-smi not found. GPU monitoring disabled.")
            return

        self.gpu_monitor_active = True
        self.log("Starting GPU monitor...", "blue")
        while self.gpu_monitor_active:
            try:
                output = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=name,driver_version,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                    text=True, stderr=subprocess.PIPE, startupinfo=subprocess.STARTUPINFO(dwFlags=subprocess.CREATE_NO_WINDOW))
                self.update_gpu_log(output.strip())
            except subprocess.CalledProcessError as e:
                self.update_gpu_log(f"Error running nvidia-smi: {e.stderr}")
                self.log("Error monitoring GPU. Disabling monitor.", "red")
                break
            except Exception as e:
                self.update_gpu_log(f"An unexpected error occurred during GPU monitoring: {e}")
                self.log("An unexpected error occurred during GPU monitoring.", "red")
                break
            time.sleep(2)
        self.log("GPU monitor stopped.", "blue")

    def stop_gpu_monitor(self):
        self.gpu_monitor_active = False

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.flv"), ("All files", "*.*")]
        )
        for f in files:
            if f not in self.video_files:
                self.video_files.append(f)
        self._update_listbox_display()

    def remove_selected(self):
        selected_indices = list(self.listbox.curselection())
        for i in reversed(selected_indices):
            del self.video_files[i]
        self.log(f"Removed {len(selected_indices)} file(s).")
        self._update_listbox_display()

    def _update_listbox_display(self):
        self.listbox.delete(0, tk.END)
        for f in self.video_files:
            self.listbox.insert(tk.END, Path(f).name)

    def select_output_dir(self):
        folder = filedialog.askdirectory(title="Select Output Directory")
        if folder:
            self.output_dir.set(folder)
            Path(folder).mkdir(exist_ok=True)
            self.log(f"Output directory set to: {folder}")

    def start_threaded_process(self):
        if not self.video_files:
            self.log("Please add video files to process.", "orange")
            return
        if not shutil.which("ffmpeg"):
            self.log("FFmpeg executable not found in your system's PATH. Cannot start processing.", "red")
            return

        self.is_processing = True
        self.cancel_requested = False
        self.pause_requested = False
        self.log("Starting batch processing...", "green")
        self._set_ui_state(processing=True)

        threading.Thread(target=self.process_batch, daemon=True).start()
        if self.monitor_gpu.get():
            threading.Thread(target=self.monitor_gpu_usage, daemon=True).start()

    def _set_ui_state(self, processing: bool):
        state = DISABLED if processing else NORMAL
        for widget in self.widgets_to_disable:
            widget.configure(state=state)
        
        self.listbox.configure(state=state)
        
        self.start_button.configure(state=state)
        self.pause_button.configure(state=NORMAL if processing else DISABLED)
        self.resume_button.configure(state=NORMAL if processing else DISABLED)
        self.cancel_button.configure(state=NORMAL if processing else DISABLED)

    def request_cancel(self):
        self.cancel_requested = True
        self.pause_requested = False
        self.log("Cancel requested. Process will stop after the current file.", "orange")
        self._update_status("Cancelling...", "warning")

    def request_pause(self):
        self.pause_requested = True
        self.log("Pausing... The current file will finish, then the process will pause.", "orange")
        self._update_status("Pausing...", "info")

    def request_resume(self):
        if self.pause_requested:
            self.pause_requested = False
            self.log("Resuming processing...", "green")
            self._update_status("Processing...", "success")

    def generate_output_filename(self, input_path, resolution, profile_name, ext):
        base = Path(input_path).stem
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        profile_clean = profile_name.replace(' ', '_').lower()
        res_str = resolution if resolution != 'Original' else 'source'
        filename = f"{base}_{res_str}_{profile_clean}_{date_str}.{ext}"
        return Path(self.output_dir.get()) / filename

    def on_closing(self):
        if self.is_processing:
            self.cancel_requested = True
            self.log("Exit requested. Finishing current task before closing...", "red")
            self.master.after(1000, self.master.destroy)
        else:
            self.master.destroy()

    def process_batch(self):
        total_files = len(self.video_files)
        for i, video_path in enumerate(self.video_files):
            if self.cancel_requested: break
            
            while self.pause_requested:
                if self.cancel_requested: break
                time.sleep(1)

            if self.cancel_requested: break

            self._update_status(f"Processing {i+1}/{total_files}: {Path(video_path).name}", "success")
            qp_val = self.qp.get()
            resolution = self.scale_var.get()
            codec = self.codec_var.get()
            ext = self.format_var.get()
            use_hwaccel = self.hw_decode.get()
            
            output_path = self.generate_output_filename(video_path, resolution, self.profile_var.get(), ext)

            ffmpeg_cmd = ["ffmpeg", "-y"]
            video_filters = []
            
            if use_hwaccel:
                ffmpeg_cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
            
            ffmpeg_cmd.extend(["-i", video_path])
            
            if use_hwaccel:
                if resolution != "Original":
                    video_filters.append(f"scale_cuda={resolution}:force_original_aspect_ratio=decrease")
                video_filters.append("nlmeans_cuda=1.5:1.5:6:6")
            else:
                if resolution != "Original":
                     video_filters.append(f"scale={resolution}:force_original_aspect_ratio=decrease")
            
            if video_filters:
                ffmpeg_cmd.extend(["-vf", ",".join(video_filters)])

            ffmpeg_cmd.extend([
                "-c:v", codec, "-rc", "constqp", "-qp", str(qp_val),
                "-preset", "p6", "-profile:v", "high", "-movflags", "+faststart"
            ])

            if self.audio_passthrough.get():
                ffmpeg_cmd.extend(["-c:a", "copy"])
            else:
                ffmpeg_cmd.extend(["-c:a", "aac", "-b:a", "192k"])

            ffmpeg_cmd.append(str(output_path))
            
            self.log(f"({i+1}/{total_files}) Processing: {Path(video_path).name}", "blue")
            self.log(f"    Output: {output_path.name}")
            
            try:
                si = subprocess.STARTUPINFO(dwFlags=subprocess.CREATE_NO_WINDOW)
                process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', startupinfo=si)
                _, stderr = process.communicate()

                if process.returncode == 0:
                    self.log(f"Completed: {output_path.name}", "green")
                else:
                    self.log(f"Failed: {output_path.name}", "red")
                    self.log(f"FFmpeg Error:\n{stderr}", "red")
                    if self.cancel_requested: break
            except Exception as e:
                self.log(f"An unexpected error occurred: {e}", "red")
                if self.cancel_requested: break

        self.stop_gpu_monitor()
        if self.cancel_requested:
            self.log("Batch processing was cancelled by the user.", "red")
            self._update_status("Cancelled", "danger")
        else:
            self.log("All videos processed successfully!", "green")
            self._update_status("Completed all tasks!", "success")
        
        self.is_processing = False
        self.pause_requested = False
        self._set_ui_state(processing=False)

if __name__ == "__main__":
    root = ttk.Window(themename="darkly")
    app = FFmpegBatchEnhancerGUI(root)
    root.mainloop()
