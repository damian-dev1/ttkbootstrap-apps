import os
import threading
import openai
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinterhtml import HtmlFrame
from tkinter import filedialog, messagebox
from datetime import datetime
import base64
import mimetypes
import tiktoken
import markdown

OPENAI_API_KEY = "your_openai_api_key_here" # this variable is here just to run the code snippet independently for demonstration purposes.
# In practice, you would import this from a config file or environment variable.

try:
    from config import OPENAI_API_KEY
    openai.api_key = OPENAI_API_KEY
except ImportError:
    pass 
except AttributeError:
    pass

SYSTEM_PROMPT_PRESETS = {
    "Default": "",
    "Default with Context": "You are a helpful assistant. Please provide context for your queries.",
    "Friendly Assistant": "You are a helpful, friendly assistant.",
    "Technical Expert": "You are a senior software engineer helping with technical questions.",
    "Productivity Coach": "You help users stay productive and focused.",
    "Creative Writer": "You assist with creative writing tasks and brainstorming ideas.",
    "Data Analyst": "You help analyze data and provide insights.",
    "Customer Support": "You assist with customer support inquiries and troubleshooting.",
    "Research Assistant": "You help with research tasks and finding information.",
    "Language Tutor": "You assist with language learning and practice.",
    "Categorization Expert": "You are an assistant that categorizes products accurately.",
    "Invoice Specialist": "You assist with invoice processing and management.",
    "Code Review Assistant": "You help with code reviews and provide feedback on code quality.",
}

THEMES = ["darkly", "solar", "superhero", "cyborg", "journal", "morph", "minty", "flatly", "pulse", "litera", "sandstone"]


class OpenAIBackend:
    def __init__(self, api_key):
        self.api_key = api_key 

    def query_openai(self, messages, model, max_tokens, temperature, top_p, freq_penalty,
                     pres_penalty, stop_sequences, seed, response_format,
                     append_response_cb, update_history_cb, update_token_cb, stream_enabled):
        
        full_text = ""
        total_tokens_used = 0

        api_params = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": freq_penalty,
            "presence_penalty": pres_penalty,
        }

        if stop_sequences:
            api_params["stop"] = stop_sequences

        if seed > 0:
            api_params["seed"] = seed

        if response_format == "json_object":
            api_params["response_format"] = {"type": "json_object"}

        try:
            encoding = tiktoken.encoding_for_model(model)

            if stream_enabled:
                api_params["stream"] = True
                response_stream = openai.ChatCompletion.create(**api_params)

                for chunk in response_stream:
                    if chunk.choices and chunk.choices[0].delta and hasattr(chunk.choices[0].delta, 'content'):
                        content = chunk.choices[0].delta.content
                        full_text += content
                        append_response_cb(content) 

                input_tokens = 0
                for msg in messages:
                    if isinstance(msg['content'], str):
                        input_tokens += len(encoding.encode(msg['content']))
                    elif isinstance(msg['content'], list): # Handle multi-modal content
                        for part in msg['content']:
                            if part['type'] == 'text':
                                input_tokens += len(encoding.encode(part['text']))
                            # Image tokens are not directly counted by tiktoken for vision models
                            # OpenAI handles internal pricing for image tokens
                output_tokens = len(encoding.encode(full_text))
                total_tokens_used = input_tokens + output_tokens

            else:
                res = openai.ChatCompletion.create(**api_params)
                full_text = res.choices[0].message.content
                append_response_cb(full_text)

                if hasattr(res, 'usage') and res.usage.total_tokens:
                    total_tokens_used = res.usage.total_tokens
                else:
                    input_tokens = 0
                    for msg in messages:
                        if isinstance(msg['content'], str):
                            input_tokens += len(encoding.encode(msg['content']))
                        elif isinstance(msg['content'], list):
                            for part in msg['content']:
                                if part['type'] == 'text':
                                    input_tokens += len(encoding.encode(part['text']))
                    output_tokens = len(encoding.encode(full_text))
                    total_tokens_used = input_tokens + output_tokens

            update_history_cb(messages, full_text)
            total_tokens_used = 0 

        except Exception as e:
            append_response_cb(f"\n\n[ERROR] An unexpected error occurred: {str(e)}")
            total_tokens_used = 0 
        finally:
            update_token_cb(total_tokens_used)
            append_response_cb("\n\n[End of response]")

class PluginError(Exception):
    """Custom exception for plugin-related errors."""
    pass
    def register_plugin(plugin_func):
        """
        Register a plugin function that can be called with the current messages and prompt.
        """
        if not hasattr(PlaygroundGUI, 'plugins'):
            PlaygroundGUI.plugins = []
        PlaygroundGUI.plugins.append(plugin_func)
        print(f"[PLUGIN] Registered plugin: {plugin_func.__name__}")

class PlaygroundGUI(ttk.Window):
    def __init__(self, backend_api):
        super().__init__(title="OpenAI Playground Pro", themename="solar", size=(1000, 925), resizable=(True, True))
        self.backend = backend_api

        self.stream_enabled = ttk.BooleanVar(value=True)
        self.markdown_enabled = ttk.BooleanVar(value=False)
        self.theme_choice = ttk.StringVar(value="solar")
        self.temp_val = ttk.DoubleVar(value=0.7)
        self.max_tokens = ttk.IntVar(value=500)
        self.top_p = ttk.DoubleVar(value=1.0)
        self.model = ttk.StringVar(value="gpt-4o")
        self.preset = ttk.StringVar(value="Default")
        self.token_used = ttk.IntVar(value=0)
        self.file_path = None
        self.attached_file_data = None 
        self.attached_file_mime_type = None
        self.response = ""

        self.freq_penalty = ttk.DoubleVar(value=0.0)
        self.pres_penalty = ttk.DoubleVar(value=0.0)
        self.stop_sequences_var = ttk.StringVar(value="")
        self.seed = ttk.IntVar(value=0)
        self.response_format_var = ttk.StringVar(value="text")
        self.plugins = []
        self.history_list = []

        self._build_topbar()
        self._build_layout()

        self.token_used.trace_add("write", lambda *args: self.token_meter.configure(amountused=self.token_used.get()))


    def _build_topbar(self):
        self.top = ttk.Frame(self)
        self.top.pack(fill=X, padx=10, pady=5)
        
        ttk.Label(self.top, text="Theme:").pack(side=LEFT)
        ttk.OptionMenu(self.top, self.theme_choice, self.theme_choice.get(), *THEMES, command=self.change_theme).pack(side=LEFT, padx=5)
        
        ttk.Label(self.top, text="System Prompt Preset:").pack(side=LEFT, padx=(15, 0))
        ttk.OptionMenu(self.top, self.preset, self.preset.get(), *SYSTEM_PROMPT_PRESETS.keys(), command=self.update_system_prompt).pack(side=LEFT, padx=5)

        ttk.Button(self.top, text="Clear History Display", command=self.clear_history_display, bootstyle=WARNING).pack(side=RIGHT, padx=5)


    def _build_layout(self):
        paned = ttk.PanedWindow(self, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(paned, padding=10)
        paned.add(left_frame, weight=3)

        self.tabs = ttk.Notebook(left_frame)
        self.tabs.pack(fill=BOTH, expand=True)

        self.chat_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.chat_tab, text="Chat")
        self._build_chat_tab()

        self.history_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.history_tab, text="History")
        self._build_history_tab()

        right_frame = ttk.Frame(paned, padding=10)
        paned.add(right_frame, weight=1)

        ttk.Label(right_frame, text="Model Settings", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=5)
        self._create_labeled_combo(right_frame, "Model", self.model, ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo-0613", "gpt-3.5-turbo-16k"])
        self._create_labeled_spin(right_frame, "Max Tokens", self.max_tokens, 50, 4096)
        self._create_labeled_combo(right_frame, "Top P", self.top_p, [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        self._create_labeled_slider(right_frame, "Temperature", self.temp_val, 0.0, 1.0)
        self._create_labeled_slider(right_frame, "Frequency Penalty", self.freq_penalty, -2.0, 2.0)
        self._create_labeled_slider(right_frame, "Presence Penalty", self.pres_penalty, -2.0, 2.0)

        ttk.Label(right_frame, text="Stop Sequences (comma-separated)", font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 0))
        ttk.Entry(right_frame, textvariable=self.stop_sequences_var).pack(fill=X)

        self._create_labeled_spin(right_frame, "Seed (0 for random)", self.seed, 0, 999999)

        self._create_labeled_combo(right_frame, "Response Format", self.response_format_var, ["text", "json_object"])


        ttk.Label(right_frame, text="Options", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=10)
        ttk.Checkbutton(right_frame, text="Stream Response", variable=self.stream_enabled).pack(anchor="w")
        ttk.Checkbutton(right_frame, text="Enable Markdown Rendering (WIP)", variable=self.markdown_enabled, state="disabled").pack(anchor="w")


        ttk.Label(right_frame, text="File", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=10)
        self.file_label = ttk.Label(right_frame, text="No file attached", bootstyle=SECONDARY)
        self.file_label.pack(anchor="w")
        ttk.Button(right_frame, text="Attach File", command=self.attach_file, bootstyle=INFO).pack(anchor="w", pady=5)

        ttk.Separator(right_frame).pack(fill=X, pady=10)

        ttk.Label(right_frame, text="Actions", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=10)
        ttk.Button(right_frame, text="Send", command=self.send, bootstyle=SUCCESS).pack(fill=X, pady=5)
        ttk.Button(right_frame, text="Clear", command=self.clear, bootstyle=WARNING).pack(fill=X, pady=5)
        ttk.Button(right_frame, text="Save Response", command=self.save_response, bootstyle=SECONDARY).pack(fill=X, pady=5)

        ttk.Separator(right_frame).pack(fill=X, pady=10)

        self.token_meter = ttk.Meter(right_frame, metersize=200, amounttotal=4096,
                                     amountused=self.token_used.get(), metertype='full',
                                     subtext="tokens used", interactive=False, bootstyle=INFO)
        self.token_meter.pack(pady=10)


    def _build_chat_tab(self):
        frame = self.chat_tab

        ttk.Label(frame, text="System Prompt", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        self.system_input = ttk.ScrolledText(frame, height=4, wrap="word")
        self.system_input.pack(fill=X, pady=5, padx=10)
        self.system_input.insert("1.0", SYSTEM_PROMPT_PRESETS["Default"])
        
        self.system_input.bind("<KeyRelease>", self._check_custom_preset) 
        self.preset.trace_add("write", lambda *args: self.update_system_prompt(self.preset.get()))


        ttk.Label(frame, text="User Prompt", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        self.user_input = ttk.ScrolledText(frame, height=6, wrap="word")
        self.user_input.pack(fill=X, padx=10, pady=5)
        # self.user_input.pack(fill=X, pady=5, padx=10)
        self.user_input.bind("<KeyRelease>", self._check_custom_preset)
        self.preset.trace_add("write", lambda *args: self.update_system_prompt(self.preset.get()))
        self.user_input.bind("<Return>", lambda e: self.send() if e.state & 0x0001 else "break")  # Shift+Enter to send
        self.preset.trace_add("write", lambda *args: self.update_system_prompt(self.preset.get()))
        self.user_input.bind("<KeyRelease>", self._check_custom_preset)

        ttk.Label(frame, text="AI Response", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        self.response_output = ttk.ScrolledText(frame, height=20, wrap="word", state="disabled")
        self.response_output.pack(fill=BOTH, expand=True, pady=5, padx=10)
        self.response_output.pack(fill=BOTH, expand=True, padx=10, pady=5)
        self.html_output = HtmlFrame(frame, horizontal_scrollbar="auto")
        self.html_output.pack_forget()

    def _append_response(self, text):
        if self.markdown_enabled.get():
            self.html_output.set_content(markdown.markdown(text))
            self.html_output.pack(fill=BOTH, expand=True, padx=10, pady=5)
            self.response_output.pack_forget()

    def _build_history_tab(self):
        self.history_box = ttk.ScrolledText(self.history_tab, height=40, wrap="word", state="disabled")
        self.history_box.pack(fill=BOTH, expand=True, padx=10, pady=10)

    def _create_labeled_combo(self, parent, label, variable, values):
        frame = ttk.Frame(parent)
        frame.pack(fill=X, pady=(5, 0))
        ttk.Label(frame, text=label).pack(anchor="w")
        ttk.Combobox(frame, textvariable=variable, values=values, state="readonly").pack(fill=X)

    def _create_labeled_spin(self, parent, label, variable, min_, max_):
        frame = ttk.Frame(parent)
        frame.pack(fill=X, pady=(5, 0))
        ttk.Label(frame, text=label).pack(anchor="w")
        ttk.Spinbox(frame, from_=min_, to=max_, textvariable=variable, width=10).pack(fill=X)

    def _create_labeled_slider(self, parent, label, variable, min_, max_):
        frame = ttk.Frame(parent)
        frame.pack(fill=X, pady=(5, 0))
        ttk.Label(frame, text=label).pack(anchor="w")
        ttk.Scale(frame, from_=min_, to=max_, variable=variable).pack(fill=X)

    def update_system_prompt(self, choice):
        if choice in SYSTEM_PROMPT_PRESETS:
            self.system_input.delete("1.0", "end")
            self.system_input.insert("1.0", SYSTEM_PROMPT_PRESETS[choice])

    def _check_custom_preset(self, event=None):
        current_text = self.system_input.get("1.0", "end").strip()
        is_preset_match = False
        for preset_name, preset_value in SYSTEM_PROMPT_PRESETS.items():
            if current_text == preset_value.strip():
                self.preset.set(preset_name)
                is_preset_match = True
                break
        
        if not is_preset_match:
            if self.preset.get() != "Custom": 
                self.preset.set("Custom")


    def change_theme(self, theme_name):
        self.style.theme_use(theme_name)

    def attach_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            try:
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type and mime_type.startswith('image/'):
                    with open(file_path, "rb") as f:
                        image_data = base64.b64encode(f.read()).decode('utf-8')
                    self.attached_file_data = image_data
                    self.attached_file_mime_type = mime_type
                    self.file_label.config(text=f"Attached: {os.path.basename(file_path)} (Image)", bootstyle=SUCCESS)
                else:
                    messagebox.showwarning("Unsupported File Type", "Only image files (PNG, JPG, etc.) are currently supported for attachment.")
                    self.attached_file_data = None
                    self.attached_file_mime_type = None
                    self.file_path = None
                    self.file_label.config(text="No file attached", bootstyle=SECONDARY)
            except Exception as e:
                messagebox.showerror("File Error", f"Could not read file: {e}")
                self.attached_file_data = None
                self.attached_file_mime_type = None
                self.file_path = None
                self.file_label.config(text="No file attached", bootstyle=SECONDARY)
        else:
            self.attached_file_data = None
            self.attached_file_mime_type = None
            self.file_path = None
            self.file_label.config(text="No file attached", bootstyle=SECONDARY)

    def clear(self):
        self.system_input.delete("1.0", "end")
        self.user_input.delete("1.0", "end")

        self.response_output.config(state="normal")
        self.response_output.delete("1.0", "end")
        self.response_output.config(state="disabled")

        self.response = ""
        self.file_path = None
        self.attached_file_data = None
        self.attached_file_mime_type = None
        self.file_label.config(text="No file attached", bootstyle=SECONDARY)
        self.token_used.set(0)

    def clear_history_display(self):
        self.history_list = []
        self.history_box.config(state="normal")
        self.history_box.delete("1.0", "end")
        self.history_box.config(state="disabled")

    def send(self):
        system_msg = self.system_input.get("1.0", "end").strip()
        user_msg = self.user_input.get("1.0", "end").strip()

        if not user_msg:
            messagebox.showerror("Validation Error", "User prompt is required to send a query.")
            return

        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        
        user_content_parts = [{"type": "text", "text": user_msg}]
        if self.attached_file_data and self.attached_file_mime_type:
            user_content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{self.attached_file_mime_type};base64,{self.attached_file_data}"
                }
            })
        messages.append({"role": "user", "content": user_content_parts})


        self.response_output.config(state="normal")
        self.response_output.delete("1.0", "end")
        self.response_output.insert("end", "[Waiting for response...]\n\n")
        self.response_output.config(state="disabled")

        threading.Thread(target=self.backend.query_openai,
                         args=(messages,
                               self.model.get(),
                               self.max_tokens.get(),
                               self.temp_val.get(),
                               self.top_p.get(),
                               self.freq_penalty.get(),
                               self.pres_penalty.get(),
                               [s.strip() for s in self.stop_sequences_var.get().strip().split(',') if s.strip()],
                               self.seed.get(),
                               self.response_format_var.get(),
                               self._append_response_safe,
                               self._update_history_safe,
                               self._update_token_used_safe,
                               self.stream_enabled.get()),
                         daemon=True).start()

    def _append_response_safe(self, text):
        self.after(0, self._append_response, text)



    def _append_response(self, text):
        self.response_output.config(state="normal")
        self.response_output.insert("end", text)
        self.response_output.see("end")
        self.response_output.config(state="disabled")



    def _update_history_safe(self, messages, reply):
        self.after(0, self._update_history, messages, reply)

    def _update_history(self, messages, reply):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        system_msg_content = "N/A"
        user_msg_content = "N/A"

        for msg in messages:
            if msg['role'] == 'system':
                system_msg_content = msg['content']
            elif msg['role'] == 'user':
                # Handle multi-modal content for history display
                user_parts = []
                if isinstance(msg['content'], str):
                    user_parts.append(msg['content'])
                elif isinstance(msg['content'], list):
                    for part in msg['content']:
                        if part['type'] == 'text':
                            user_parts.append(part['text'])
                        elif part['type'] == 'image_url':
                            user_parts.append("[Image Attached]")
                user_msg_content = "\n".join(user_parts)


        log_entry = f"--- Conversation Entry [{timestamp}] ---\n"
        if system_msg_content != "N/A":
            log_entry += f"System: {system_msg_content}\n"
        log_entry += f"User: {user_msg_content}\n"
        log_entry += f"AI: {reply}\n\n"

        self.history_list.append(log_entry)
        self.history_box.config(state="normal")
        self.history_box.insert("end", log_entry)
        self.history_box.see("end")
        self.history_box.config(state="disabled")

        self.response = reply

    def _update_token_used_safe(self, tokens):
        self.after(0, self.token_used.set, tokens)

    def _update_token_used(self, tokens):
        self.token_used.set(tokens)
        self.token_meter.configure(amountused=tokens)

        if tokens > 4096:
            messagebox.showwarning("Token Limit Exceeded", "You have exceeded the maximum token limit for this request.")


    def save_response(self):
        if not self.response.strip():
            messagebox.showwarning("No Response", "Nothing to save yet. Generate a response first.")
            return

        file = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file:
            try:
                with open(file, "w", encoding="utf-8") as f:
                    f.write(self.response)
                messagebox.showinfo("Saved", "Response saved successfully.")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save file: {e}")

class MainApp:
    def __init__(self):
        # try:
        #     from config import OPENAI_API_KEY
        #     if not OPENAI_API_KEY:
        #         raise ValueError("OPENAI_API_KEY is empty in config.py")
        # except ImportError:
        #     messagebox.showerror(
        #         "Configuration Error", 
        #         "config.py not found. Please create a config.py file with OPENAI_API_KEY = 'your_key_here'"
        #     )
        #     exit()
        # except ValueError as e:
        #     messagebox.showerror("Configuration Error", str(e))
        #     exit()
        # except Exception as e:
        #     messagebox.showerror("Initialization Error", f"An unexpected error occurred during API key setup: {e}")
        #     exit()

        self.backend = OpenAIBackend(api_key=OPENAI_API_KEY)
        self.gui = PlaygroundGUI(backend_api=self.backend)
        self.gui.protocol("WM_DELETE_WINDOW", self.gui.destroy)
        self.gui.bind("<Control-q>", lambda e: self.gui.destroy())
        
        def summarize_length(messages, prompt):
            print(f"[PLUGIN] Prompt length: {len(prompt)} tokens")



    def run(self):
        start_time = datetime.now()
        print(f"Starting OpenAI Playground Pro at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.gui.mainloop()
        
        end_time = datetime.now()
        print(f"Application closed. Time taken: {round((end_time - start_time).total_seconds(), 2)} seconds")

        def sample_plugin(messages, prompt):
            print(f"[PLUGIN] User prompt length: {len(prompt)}")


if __name__ == "__main__":
    app = MainApp()
    app.run()
