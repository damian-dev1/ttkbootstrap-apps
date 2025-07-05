import os
import sys
import shutil
import time
import datetime
import subprocess
import threading
import queue
import tkinter as tk
from tkinter import filedialog, scrolledtext
from tkinter import LEFT, RIGHT, BOTH, DISABLED, NORMAL, EXTENDED  # Removed unused: N, S, E, W, NSEW, EW, X
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pathlib import Path
import ctypes
import csv
from datetime import datetime

ffmpeg_bin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin")
if os.path.isdir(ffmpeg_bin):
    os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ["PATH"]

class VideoBenchmarkLogger:
    def __init__(self, log_dir="benchmark_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.records = []

    def log(self, input_path, output_path, filter_chain, duration_sec, size_bytes, codec, success, error=""):
        record = {
            "input": str(input_path),
            "output": str(output_path),
            "filters": filter_chain,
            "duration_sec": round(duration_sec, 3),
            "size_kb": round(size_bytes / 1024, 2),
            "codec": codec,
            "success": success,
            "error": error.strip()[:300] if error else ""
        }
        self.records.append(record)

    def save(self):
        if not self.records:
            return
        with open(self.log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.records[0].keys())
            writer.writeheader()
            writer.writerows(self.records)




# filters_to_test = [
#     "nlmeans=strength=4.0",
#     "bilateral_cuda=diameter=5",
#     "yadif_cuda=1"
# ]

# bench.benchmark_filters(
#     input_path="C:/Users/damian/projects/videos/media-assets/Dash cam accident (1).mp4",
#     filter_list=filters_to_test,
#     resolution="1920:1080"
# )

# bench.save_results_csv("C:/Users/damian/Desktop/benchmark_results.csv")

# for r in bench.get_results():
#     print(r)

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



class FFmpegFilterBenchmark:
    def __init__(self, ffmpeg_path="ffmpeg", output_dir="benchmark_outputs"):
        self.ffmpeg_path = ffmpeg_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []

    def benchmark_filter(self, input_path, filters, output_suffix=None, codec="h264_nvenc", resolution=None):
        input_path = Path(input_path)
        filename = input_path.stem
        extension = input_path.suffix
        if output_suffix is None:
            output_suffix = filters.replace("=", "_").replace(",", "-").replace(":", "-")

        output_file = self.output_dir / f"{filename}_{output_suffix}{extension}"

        filter_chain = filters
        if resolution:
            filter_chain = f"scale={resolution}, {filters}"

        cmd = [
            self.ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(input_path),
            "-vf", filter_chain,
            "-c:v", codec,
            "-b:v", "5M",
            "-preset", "p4",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_file)
        ]

        start_time = time.time()
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        end_time = time.time()
        duration = round(end_time - start_time, 3)

        file_size = output_file.stat().st_size if output_file.exists() else 0

        result = {
            "input": str(input_path),
            "filter": filters,
            "output": str(output_file),
            "duration_sec": duration,
            "size_bytes": file_size,
            "success": process.returncode == 0,
            "return_code": process.returncode,
            "error": process.stderr.strip() if process.returncode != 0 else ""
        }

        self.results.append(result)
        return result

    def benchmark_filters(self, input_path, filter_list, codec="h264_nvenc", resolution=None):
        for f in filter_list:
            self.benchmark_filter(input_path, f, codec=codec, resolution=resolution)

    def save_results_csv(self, csv_path="benchmark_results.csv"):
        if not self.results:
            return
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
            writer.writeheader()
            writer.writerows(self.results)

    def get_results(self):
        return self.results

class FFmpegBatchEnhancerGUI:
    THEMES = sorted(["darkly", "solar", "superhero", "cyborg", "vapor", "morph", "minty", "flatly", "pulse", "litera", "sandstone", "cosmo"])

    def __init__(self, master):
        
        self.master = master
        self.style = master.style
        self.master.title("🎬 GPU Batch Video Enhancer (FFmpeg + NVENC)")
        self.master.geometry("1000x950")
        self.master.minsize(800, 700)
        self.benchmark_logger = VideoBenchmarkLogger()
        self.profiles = {
            "Custom": None,
            "4K High Quality (HEVC)": Profile("4K High Quality (HEVC)", 18, "hevc_nvenc", "3840x2160"),
            "1080p Balanced (H.264)": Profile("1080p Balanced (H.264)", 22, "h264_nvenc", "1920x1080"),
            "1080p Web (H.264)": Profile("1080p Web (H.264)", 23, "h264_nvenc", "1920x1080"),
            "720p Web (H.264)": Profile("720p Web (H.264)", 24, "h264_nvenc", "1280x720"),
            "Archival (HEVC)": Profile("Archival (HEVC)", 17, "hevc_nvenc", "Original"),
        }

        self.video_files = []
        self.output_dir = tk.StringVar(value=str(Path.home() / "Videos" / "Enhanced"))
        self.qp = tk.IntVar(value=22)
        self.scale_var = tk.StringVar(value="1920x1080")
        self.format_var = tk.StringVar(value="mp4")
        self.codec_var = tk.StringVar(value="h264_nvenc")
        self.hw_decode = tk.BooleanVar(value=True)
        self.audio_passthrough = tk.BooleanVar(value=True)
        self.denoise = tk.BooleanVar(value=True)
        self.monitor_gpu = tk.BooleanVar(value=True)
        self.profile_var = tk.StringVar(value="1080p Balanced (H.264)")
        self.status_text = tk.StringVar()
        self.theme_var = tk.StringVar(value=self.style.theme.name)
        
        self.is_processing = False
        self.cancel_requested = False
        self.pause_requested = False
        self.gpu_monitor_thread = None
        self.processing_thread = None
        self.current_process = None

        self.ui_queue = queue.Queue()
        self.widgets_to_disable = []

        self.setup_gui()
        self.master.after(100, self.process_ui_queue)
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._check_dependencies()
        self.apply_preset()
        self.benchmark_logger.save()

    def _check_dependencies(self):
        if not shutil.which("ffmpeg"):
            self.log("FFmpeg not found. Please ensure ffmpeg.exe is in the path or in a subfolder named 'ffmpeg/bin'.", "danger")
        if not shutil.which("nvidia-smi"):
            self.log("NVIDIA-SMI not found. GPU monitoring will be disabled.", "warning")
            self.monitor_gpu.set(False)
            self.monitor_gpu_check.configure(state=DISABLED)

    def setup_gui(self):
        main_frame = ttk.Frame(self.master, padding=15)
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
        button_frame.grid(row=0, column=0, columnspan=2, pady=5, sticky=W)
        self.add_button = ttk.Button(button_frame, text="➕ Add Videos", command=self.add_files, bootstyle=SUCCESS)
        self.add_button.pack(side=LEFT, padx=5, pady=5)
        self.remove_button = ttk.Button(button_frame, text="🗑 Remove Selected", command=self.remove_selected, bootstyle=DANGER)
        self.remove_button.pack(side=LEFT, padx=5, pady=5)
        self.listbox = tk.Listbox(frm_top, height=8, selectmode=EXTENDED, relief=tk.FLAT)
        self.listbox.grid(row=1, column=0, padx=5, pady=5, sticky=NSEW)
        list_scroll = ttk.Scrollbar(frm_top, orient=VERTICAL, command=self.listbox.yview)
        list_scroll.grid(row=1, column=1, sticky="ns", pady=5)
        self.listbox['yscrollcommand'] = list_scroll.set
        frm_top.grid_rowconfigure(1, weight=1)
        frm_top.grid_columnconfigure(0, weight=1)

        out_path_frame = ttk.Frame(frm_top)
        out_path_frame.grid(row=2, column=0, columnspan=2, sticky=EW, padx=5, pady=(5,10))
        out_path_frame.columnconfigure(0, weight=1)
        self.output_entry = ttk.Entry(out_path_frame, textvariable=self.output_dir)
        self.output_entry.grid(row=0, column=0, sticky=EW, padx=(0,5))
        self.output_button = ttk.Button(out_path_frame, text="📁 Select Output Folder", command=self.select_output_dir, bootstyle=INFO)
        self.output_button.grid(row=0, column=1, sticky=E)

        frm_opts = ttk.LabelFrame(main_frame, text="Encoding Settings", bootstyle=INFO)
        frm_opts.pack(fill=X, pady=10)
        frm_opts.columnconfigure((1, 3), weight=1)

        ttk.Label(frm_opts, text="🎯 Preset Profile:", bootstyle=PRIMARY).grid(row=0, column=0, padx=5, pady=5, sticky=W)
        self.profile_combobox = ttk.Combobox(frm_opts, textvariable=self.profile_var, values=list(self.profiles.keys()), state="readonly", bootstyle=INFO)
        self.profile_combobox.grid(row=0, column=1, padx=5, pady=5, sticky=EW)
        self.profile_var.trace_add("write", self.apply_preset)

        ttk.Label(frm_opts, text="🎥 Codec:", bootstyle=PRIMARY).grid(row=0, column=2, padx=15, pady=5, sticky=W)
        self.codec_combobox = ttk.Combobox(frm_opts, textvariable=self.codec_var, values=["h264_nvenc", "hevc_nvenc"], state="readonly", bootstyle=INFO)
        self.codec_combobox.grid(row=0, column=3, padx=5, pady=5, sticky=EW)

        ttk.Label(frm_opts, text="📁 Output Format:", bootstyle=PRIMARY).grid(row=1, column=0, padx=5, pady=5, sticky=W)
        self.format_combobox = ttk.Combobox(frm_opts, textvariable=self.format_var, values=["mp4", "mkv"], state="readonly", bootstyle=INFO)
        self.format_combobox.grid(row=1, column=1, padx=5, pady=5, sticky=EW)

        ttk.Label(frm_opts, text="🖼 Resolution:", bootstyle=PRIMARY).grid(row=1, column=2, padx=15, pady=5, sticky=W)
        self.scale_combobox = ttk.Combobox(frm_opts, textvariable=self.scale_var, values=["Original", "3840x2160", "2560x1440", "1920x1080", "1280x720"], state="readonly", bootstyle=INFO)
        self.scale_combobox.grid(row=1, column=3, padx=5, pady=5, sticky=EW)
        
        ttk.Label(frm_opts, text="🔧 QP (Quality, 0-51):", bootstyle=PRIMARY).grid(row=2, column=0, padx=5, pady=5, sticky=W)
        self.qp_spinbox = ttk.Spinbox(frm_opts, from_=0, to=51, textvariable=self.qp, width=8, bootstyle=INFO)
        self.qp_spinbox.grid(row=2, column=1, padx=5, pady=5, sticky=W)

        check_frame = ttk.Frame(frm_opts)
        check_frame.grid(row=3, column=0, columnspan=4, pady=10, sticky=W)
        self.hw_decode_check = ttk.Checkbutton(check_frame, text="Enable NVDEC Hardware Decode", variable=self.hw_decode, bootstyle="round-toggle")
        self.hw_decode_check.pack(side=LEFT, padx=5)
        self.audio_passthrough_check = ttk.Checkbutton(check_frame, text="Copy Audio (Passthrough)", variable=self.audio_passthrough, bootstyle="round-toggle")
        self.audio_passthrough_check.pack(side=LEFT, padx=15)
        self.denoise_check = ttk.Checkbutton(check_frame, text="Apply Denoise Filter", variable=self.denoise, bootstyle="round-toggle")
        self.denoise_check.pack(side=LEFT, padx=5)
        self.monitor_gpu_check = ttk.Checkbutton(check_frame, text="Monitor GPU", variable=self.monitor_gpu, bootstyle="round-toggle")
        self.monitor_gpu_check.pack(side=LEFT, padx=15)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        self.start_button = ttk.Button(btn_frame, text="🚀 Start Encoding", command=self.start_processing, width=20, bootstyle=SUCCESS)
        self.start_button.grid(row=0, column=0, padx=10)
        self.pause_button = ttk.Button(btn_frame, text="⏸ Pause", command=self.toggle_pause, width=15, bootstyle=WARNING, state=DISABLED)
        self.pause_button.grid(row=0, column=1, padx=5)
        self.cancel_button = ttk.Button(btn_frame, text="❌ Cancel", command=self.request_cancel, width=15, bootstyle=DANGER, state=DISABLED)
        self.cancel_button.grid(row=0, column=2, padx=5)

        self.widgets_to_disable.extend([
            self.add_button, self.remove_button, self.output_button, self.output_entry,
            self.profile_combobox, self.codec_combobox, self.format_combobox, self.listbox,
            self.scale_combobox, self.qp_spinbox, self.hw_decode_check,
            self.audio_passthrough_check, self.denoise_check, self.monitor_gpu_check, self.theme_combobox
        ])

        paned_window = ttk.PanedWindow(main_frame, orient=VERTICAL)
        paned_window.pack(fill=BOTH, expand=True, pady=5)
        
        log_frame = ttk.LabelFrame(paned_window, text="Processing Log", bootstyle=PRIMARY)
        self.log_output = scrolledtext.ScrolledText(log_frame, wrap="word", height=10, font=("Segoe UI", 9), relief=tk.FLAT, state=DISABLED)
        self.log_output.pack(padx=5, pady=5, fill=BOTH, expand=True)
        paned_window.add(log_frame, weight=3)

        gpu_frame = ttk.LabelFrame(paned_window, text="GPU Usage Monitor", bootstyle=PRIMARY)
        self.gpu_output = scrolledtext.ScrolledText(gpu_frame, wrap="word", height=4, font=("Consolas", 10), relief=tk.FLAT, state=DISABLED)
        self.gpu_output.pack(padx=5, pady=5, fill=BOTH, expand=True)
        paned_window.add(gpu_frame, weight=1)

        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=X, side=BOTTOM, pady=(5,0))
        self.progress_bar = ttk.Progressbar(status_frame, mode='determinate')
        self.progress_bar.pack(fill=X, padx=5, pady=2)
        self.status_label = ttk.Label(status_frame, textvariable=self.status_text, anchor=W)
        self.status_label.pack(fill=X, padx=5, pady=2)
        
        self.log("Application started. Ready for video processing.", "info")
        Path(self.output_dir.get()).mkdir(parents=True, exist_ok=True)
        self._update_status("Ready", "info")

    def process_ui_queue(self):
        try:
            while True:
                task, args, kwargs = self.ui_queue.get_nowait()
                task(*args, **kwargs)
        except queue.Empty:
            pass
        finally:
            self.master.after(100, self.process_ui_queue)

    def _change_theme(self, event=None):
        selected_theme = self.theme_var.get()
        self.style.theme_use(selected_theme)
        self._update_status(f"Theme changed to {selected_theme}", "info")
        self.log(f"Theme changed to {selected_theme}", "info")
        self.configure_log_tags()

    def configure_log_tags(self):
        self.log_output.configure(state=NORMAL)
        tag_map = { "success": "green", "danger": "red", "info": "blue", "warning": "orange" }
        for name in tag_map:
            self.log_output.tag_config(name, foreground=self.style.colors.get(name))
        self.log_output.tag_config("default", foreground=self.style.colors.get('fg'))
        self.log_output.configure(state=DISABLED)

    def apply_preset(self, *args):
        profile_name = self.profile_var.get()
        profile = self.profiles.get(profile_name)
        if profile:
            profile.apply(self)
            self.log(f"Applied '{profile_name}' preset.", "success")
        else:
            self.profile_var.set("Custom")

    def _log(self, msg, tag="default"):
        timestamp = time.strftime("[%H:%M:%S]")
        self.log_output.configure(state=NORMAL)
        self.log_output.insert(tk.END, f"{timestamp} {msg}\n", tag)
        self.log_output.see(tk.END)
        self.log_output.configure(state=DISABLED)

    def log(self, msg, tag="default"):
        self.ui_queue.put((self._log, [msg, tag], {}))

    def _update_gpu_log(self, msg):
        self.gpu_output.configure(state=NORMAL)
        self.gpu_output.delete("1.0", tk.END)
        self.gpu_output.insert(tk.END, msg)
        self.gpu_output.configure(state=DISABLED)

    def update_gpu_log(self, msg):
        self.ui_queue.put((self._update_gpu_log, [msg], {}))

    def _update_status(self, text, bootstyle="default"):
        self.status_text.set(text)
        self.status_label.configure(bootstyle=bootstyle)

    def update_status(self, text, bootstyle="default"):
        self.ui_queue.put((self._update_status, [text, bootstyle], {}))

    def _update_progress(self, value):
        self.progress_bar['value'] = value

    def update_progress(self, value):
        self.ui_queue.put((self._update_progress, [value], {}))

    def monitor_gpu_usage(self):
        while not self.cancel_requested:
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
                output = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=name,driver_version,utilization.gpu,memory.used,memory.total", "--format=csv,noheader"],
                    text=True, stderr=subprocess.PIPE, startupinfo=si)
                gpu_name, driver, util, mem_used, mem_total = output.strip().split(',')
                formatted_msg = (f"{gpu_name.strip()} (Driver: {driver.strip()})\n"
                                 f"Usage: {util.strip()} | VRAM: {mem_used.strip()} / {mem_total.strip()}")
                self.update_gpu_log(formatted_msg)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                self.update_gpu_log("GPU monitoring failed. Is nvidia-smi in your PATH?")
                self.log("Disabling GPU monitor due to an error.", "danger")
                break
            except Exception as e:
                self.update_gpu_log(f"An unexpected GPU monitoring error occurred: {e}")
                break
            time.sleep(2)

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.flv"), ("All files", "*.*")]
        )
        for f in files:
            if f not in self.video_files:
                self.video_files.append(f)
                self.listbox.insert(tk.END, Path(f).name)
        self.log(f"Added {len(files)} file(s) to the queue.")

    def remove_selected(self):
        selected_indices = list(self.listbox.curselection())
        for i in reversed(selected_indices):
            del self.video_files[i]
            self.listbox.delete(i)
        self.log(f"Removed {len(selected_indices)} file(s).")

    def select_output_dir(self):
        folder = filedialog.askdirectory(title="Select Output Directory")
        if folder:
            self.output_dir.set(folder)
            Path(folder).mkdir(exist_ok=True)
            self.log(f"Output directory set to: {folder}", "info")

    def start_processing(self):
        if not self.video_files:
            self.log("Please add video files to process.", "warning")
            return
        if not shutil.which("ffmpeg"):
            self.log("FFmpeg not found. Cannot start processing.", "danger")
            return

        self.is_processing = True
        self.cancel_requested = False
        self.pause_requested = False
        self.log("Starting batch processing...", "success")
        self._set_ui_state(processing=True)

        self.processing_thread = threading.Thread(target=self.process_batch, daemon=True)
        self.processing_thread.start()
        
        if self.monitor_gpu.get() and shutil.which("nvidia-smi"):
            self.gpu_monitor_thread = threading.Thread(target=self.monitor_gpu_usage, daemon=True)
            self.gpu_monitor_thread.start()

    def _set_ui_state(self, processing: bool):
        state = DISABLED if processing else NORMAL
        for widget in self.widgets_to_disable:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass
        
        self.start_button.configure(state=state)
        self.pause_button.configure(state=NORMAL if processing else DISABLED)
        self.cancel_button.configure(state=NORMAL if processing else DISABLED)

        if not processing:
            self.pause_button.configure(text="⏸ Pause")
            self.update_progress(0)

    def set_ui_state(self, processing: bool):
        self.ui_queue.put((self._set_ui_state, [processing], {}))

    def request_cancel(self):
        if self.is_processing:
            self.cancel_requested = True
            if self.current_process:
                self.log("Cancellation requested. Terminating current FFmpeg process...", "warning")
                self.current_process.terminate()
            self.update_status("Cancelling...", "warning")

    def toggle_pause(self):
        self.pause_requested = not self.pause_requested
        if self.pause_requested:
            self.log("Pausing after current file.", "warning")
            self.update_status("Pausing...", "info")
            self.pause_button.configure(text="▶ Resume")
        else:
            self.log("Resuming processing...", "success")
            self.update_status("Processing...", "success")
            self.pause_button.configure(text="⏸ Pause")

    def generate_output_filename(self, input_path, resolution, profile_name, ext):
        base = Path(input_path).stem
        # Remove the unused date_str variable
        profile_clean = profile_name.replace(' ', '_').lower().replace('(','').replace(')','')
        res_str = resolution.split('x')[1] + 'p' if resolution != 'Original' else 'source'
        filename = f"{base}_{res_str}_{profile_clean}.{ext}"
        return Path(self.output_dir.get()) / filename

    def on_closing(self):
        if self.is_processing:
            self.request_cancel()
            self.master.title("🎬 GPU Batch Video Enhancer (CLOSING - PLEASE WAIT...)")
            self.log("Exit requested. Finishing current task before closing...", "danger")
            
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=10)
        
        self.master.destroy()

    def process_batch(self):
        total_files = len(self.video_files)
        self.update_progress(0)

        for i, video_path in enumerate(self.video_files):
            if self.cancel_requested:
                break
            
            while self.pause_requested:
                if self.cancel_requested: break
                time.sleep(1)
            
            if self.cancel_requested:
                break
            
            self.update_status(f"Processing {i+1}/{total_files}: {Path(video_path).name}", "success")
            self.process_single_file(video_path, i, total_files)
            self.update_progress((i + 1) / total_files * 100)
            self.benchmark_logger.save()
        self.cleanup_processing()

    def process_single_file(self, video_path, index, total):
        qp_val = self.qp.get()
        resolution = self.scale_var.get()
        codec = self.codec_var.get()
        ext = self.format_var.get()
        use_hwaccel = self.hw_decode.get()
        use_denoise = self.denoise.get()

        output_path = self.generate_output_filename(video_path, resolution, self.profile_var.get(), ext)

        cmd = ["ffmpeg", "-y", "-hide_banner"]
        video_filters = []

        if use_hwaccel:
            cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
        cmd.extend(["-i", str(video_path)])

        if resolution != "Original":
            filter_name = "scale_cuda" if use_hwaccel else "scale"
            video_filters.append(f"{filter_name}={resolution}:force_original_aspect_ratio=decrease")
        
        if use_denoise:
            if use_hwaccel:
                video_filters.append("nlmeans_cuda=strength=4.0")
            else:
                video_filters.append("nlmeans=strength=4.0")

        if video_filters:
            cmd.extend(["-vf", ",".join(video_filters)])

        cmd.extend([
            "-c:v", codec, "-rc", "constqp", "-qp", str(qp_val),
            "-preset", "p7", "-profile:v", "high", "-movflags", "+faststart"
        ])
        
        if self.audio_passthrough.get():
            cmd.extend(["-c:a", "copy"])
        else:
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])

        cmd.append(str(output_path))
        
        self.log(f"({index+1}/{total}) Processing: {Path(video_path).name}", "info")
        self.log(f"  └── Command: {' '.join(cmd)}")

        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', startupinfo=si)

            for line in self.current_process.stdout:
                if "No such filter: 'nlmeans_cuda'" in line and use_hwaccel:
                    self.log("nlmeans_cuda filter not found. Ensure your FFmpeg build supports it. Denoising for this file will be skipped.", "warning")
                    break
            
            self.current_process.wait()
            returncode = self.current_process.returncode
            self.current_process = None

            if returncode == 0:
                self.log(f"Successfully processed: {output_path.name}", "success")
            else:
                if not self.cancel_requested:
                    self.log(f"Error processing {Path(video_path).name}. FFmpeg exited with code {returncode}.", "danger")
        
        except FileNotFoundError:
            self.log("ffmpeg.exe not found. Please ensure it is in your system PATH.", "danger")
            self.cancel_requested = True
        except Exception as e:
            if not self.cancel_requested:
                self.log(f"An unexpected error occurred: {e}", "danger")

    def cleanup_processing(self):
        if self.cancel_requested:
            self.log("Batch processing was cancelled by the user.", "danger")
            self.update_status("Cancelled", "danger")
        else:
            self.log("All videos processed successfully!", "success")
            self.update_status("Completed all tasks!", "success")

        self.is_processing = False
        self.pause_requested = False
        self.set_ui_state(processing=False)
        self.update_gpu_log("GPU monitor idle.")

if __name__ == "__main__":
    try:
        if sys.platform.startswith("win"):
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass

    root = ttk.Window(themename="darkly")
    app = FFmpegBatchEnhancerGUI(root)
    
    try:
        icon_path = Path(__file__).parent / "favicon.ico"
        if icon_path.exists():
            root.iconbitmap(str(icon_path))
        if sys.platform.startswith("win"):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("google.gemini.ffmpeg.enhancer")
    except Exception as e:
        app.log(f"Could not set window icon: {e}", "warning")

    root.mainloop()
