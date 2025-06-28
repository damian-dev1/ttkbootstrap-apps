import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox
import requests
import json
from ttkbootstrap import Style, Window, ttk
import os

class ApiClientApp:
    def __init__(self, root, style=None):
        self.root = root
        self.style = style if style else Style(theme="superhero")
        self.root.title("API Client - Tkinter Bootstrap")
        self.root.geometry("500x1000")

        self.history_file = "api_client_history.json"
        self.saved_requests = self._load_requests_history()

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.request_tab = ttk.Frame(self.notebook, padding="10")
        self.response_tab = ttk.Frame(self.notebook, padding="10")
        self.history_tab = ttk.Frame(self.notebook, padding="10")
        self.settings_tab = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(self.request_tab, text="Request")
        self.notebook.add(self.response_tab, text="Response")
        self.notebook.add(self.history_tab, text="History")
        self.notebook.add(self.settings_tab, text="Settings")

        self.request_tab.grid_columnconfigure(0, weight=1)
        self.request_tab.grid_rowconfigure(0, weight=0)
        self.request_tab.grid_rowconfigure(1, weight=0)
        self.request_tab.grid_rowconfigure(2, weight=1)
        self.request_tab.grid_rowconfigure(3, weight=1)
        self.request_tab.grid_rowconfigure(4, weight=2)
        self.request_tab.grid_rowconfigure(5, weight=0)

        self.response_tab.grid_columnconfigure(0, weight=1)
        self.response_tab.grid_columnconfigure(1, weight=1)
        self.response_tab.grid_rowconfigure(2, weight=1)
        self.response_tab.grid_rowconfigure(4, weight=3)

        self.history_tab.grid_columnconfigure(0, weight=1)
        self.history_tab.grid_rowconfigure(0, weight=1)

        self.settings_tab.grid_columnconfigure(1, weight=1)
        self.settings_tab.grid_rowconfigure(0, weight=0)
        self.settings_tab.grid_rowconfigure(1, weight=0)
        self.settings_tab.grid_rowconfigure(2, weight=0)
        self.settings_tab.grid_rowconfigure(3, weight=0)

        # self.virtualstock_tab = ttk.Frame(self.notebook, padding="10")
        # self.notebook.add(self.virtualstock_tab, text="Virtualstock Orders")
        # self.virtualstock_tab.grid_columnconfigure(0, weight=1)
        # self.virtualstock_tab.grid_rowconfigure(1, weight=1)


        self.request_config_frame = ttk.LabelFrame(self.request_tab, text="Request Configuration", padding="10")
        self.request_config_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.request_config_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(self.request_config_frame, text="Method:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.method_combobox = ttk.Combobox(self.request_config_frame,
                                            values=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                                            state="readonly", bootstyle="info")
        self.method_combobox.set("GET")
        self.method_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(self.request_config_frame, text="URL:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.url_entry = ttk.Entry(self.request_config_frame, bootstyle="info")
        self.url_entry.insert(0, "https://jsonplaceholder.typicode.com/todos/1")
        self.url_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        self.auth_frame = ttk.LabelFrame(self.request_tab, text="Authentication (Basic Auth)", padding="10")
        self.auth_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.auth_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(self.auth_frame, text="Username:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.auth_username_entry = ttk.Entry(self.auth_frame, bootstyle="info")
        self.auth_username_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(self.auth_frame, text="Password:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.auth_password_entry = ttk.Entry(self.auth_frame, show="*", bootstyle="info")
        self.auth_password_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        self.query_params_frame = ttk.LabelFrame(self.request_tab, text="Query Parameters (Key: Value)", padding="10")
        self.query_params_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        self.query_params_frame.grid_columnconfigure(0, weight=1)
        self.query_params_frame.grid_rowconfigure(0, weight=1)

        self.query_params_text = scrolledtext.ScrolledText(self.query_params_frame, height=5, wrap=tk.WORD)
        self.query_params_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.headers_frame = ttk.LabelFrame(self.request_tab, text="Headers (Key: Value)", padding="10")
        self.headers_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        self.headers_frame.grid_columnconfigure(0, weight=1)
        self.headers_frame.grid_rowconfigure(0, weight=1)

        self.headers_text = scrolledtext.ScrolledText(self.headers_frame, height=8, wrap=tk.WORD)
        self.headers_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.headers_text.insert(tk.END, "content-type: application/json")
        self.headers_text.insert(tk.END, "Accept: application/json")

        self.body_frame = ttk.LabelFrame(self.request_tab, text="Request Body", padding="10")
        self.body_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 10))
        self.body_frame.grid_columnconfigure(1, weight=1)
        self.body_frame.grid_rowconfigure(1, weight=1)

        ttk.Label(self.body_frame, text="Body Type:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.body_type_combobox = ttk.Combobox(self.body_frame,
                                               values=["Raw (JSON)", "None", "Form Data (x-www-form-urlencoded)"],
                                               state="readonly", bootstyle="info")
        self.body_type_combobox.set("Raw (JSON)")
        self.body_type_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        self.body_text = scrolledtext.ScrolledText(self.body_frame, wrap=tk.WORD)
        self.body_text.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.body_text.insert(tk.END, '{\n  "title": "foo",\n  "body": "bar",\n  "userId": 1\n}')

        self.send_button = ttk.Button(self.request_tab, text="Send Request", command=self.send_request, bootstyle="primary")
        self.send_button.grid(row=5, column=0, sticky="ew", padx=5, pady=10)

        self.cancel_button = ttk.Button(self.request_tab, text="Cancel Request", command=self.cancel_request, bootstyle="danger-outline")
        self.cancel_button.grid(row=5, column=1, sticky="ew", padx=5, pady=10)

        ttk.Label(self.response_tab, text="Status:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.status_label = ttk.Label(self.response_tab, text="N/A", font=("TkDefaultFont", 10, "bold"), bootstyle="secondary")
        self.status_label.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(self.response_tab, text="Response Headers:").grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        self.response_headers_text = scrolledtext.ScrolledText(self.response_tab, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.response_headers_text.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.copy_headers_button = ttk.Button(self.response_tab, text="Copy Headers", command=lambda: self._copy_to_clipboard(self.response_headers_text.get(1.0, tk.END)), bootstyle="secondary-outline")
        self.copy_headers_button.grid(row=1, column=1, sticky="e", padx=5, pady=5)

        ttk.Label(self.response_tab, text="Response Body:").grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        self.response_body_text = scrolledtext.ScrolledText(self.response_tab, wrap=tk.WORD, state=tk.DISABLED)
        self.response_body_text.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.copy_body_button = ttk.Button(self.response_tab, text="Copy Body", command=lambda: self._copy_to_clipboard(self.response_body_text.get(1.0, tk.END)), bootstyle="secondary-outline")
        self.copy_body_button.grid(row=3, column=1, sticky="e", padx=5, pady=5)

        self.status_bar = ttk.Label(root, text="Ready", relief=tk.SUNKEN, anchor=tk.W, bootstyle="secondary")
        self.status_bar.grid(row=1, column=0, columnspan=1, sticky="ew")

        self.clear_button = ttk.Button(self.response_tab, text="Clear Response", command=self._clear_response_fields, bootstyle="warning-outline")
        self.clear_button.grid(row=0, column=1, sticky="e", padx=5, pady=5)

        self.theme_selector_frame = ttk.LabelFrame(self.settings_tab, text="Theme Selector", padding="10")
        self.theme_selector_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.theme_selector_frame.grid_columnconfigure(1, weight=1)

        # self.fetch_vs_button = ttk.Button(
        #     self.virtualstock_tab, text="Fetch Orders", command=self._fetch_virtualstock_orders, bootstyle="primary"
        # )
        # self.fetch_vs_button.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # self.orders_output = scrolledtext.ScrolledText(self.virtualstock_tab, wrap="word", height=20)
        # self.orders_output.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)



        ttk.Label(self.theme_selector_frame, text="Select Theme:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.theme_combobox = ttk.Combobox(self.theme_selector_frame,
                                           values=self.style.theme_names(),
                                           state="readonly", bootstyle="info")
        self.theme_combobox.set(self.style.theme.name)
        self.theme_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.theme_combobox.bind("<<ComboboxSelected>>", self._change_theme)

        self.request_settings_frame = ttk.LabelFrame(self.settings_tab, text="Request Settings", padding="10")
        self.request_settings_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.request_settings_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(self.request_settings_frame, text="Timeout (seconds):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.timeout_var = tk.DoubleVar(value=10.0)
        self.timeout_entry = ttk.Entry(self.request_settings_frame, textvariable=self.timeout_var, bootstyle="info")
        self.timeout_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        self.follow_redirects_var = tk.BooleanVar(value=True)
        self.follow_redirects_check = ttk.Checkbutton(self.request_settings_frame, text="Follow Redirects",
                                                     variable=self.follow_redirects_var, bootstyle="round-toggle")
        self.follow_redirects_check.grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        self.ssl_verify_var = tk.BooleanVar(value=True)
        self.ssl_verify_check = ttk.Checkbutton(self.request_settings_frame, text="Verify SSL Certificates",
                                               variable=self.ssl_verify_var, bootstyle="round-toggle")
        self.ssl_verify_check.grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        self.history_frame = ttk.LabelFrame(self.history_tab, text="Saved Requests", padding="10")
        self.history_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.history_frame.grid_columnconfigure(0, weight=1)
        self.history_frame.grid_rowconfigure(0, weight=1)

        self.history_listbox = tk.Listbox(self.history_frame, selectmode=tk.SINGLE)
        self.history_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.history_listbox.bind("<<ListboxSelect>>", self._on_history_select)
        self._populate_history_listbox()

        self.history_buttons_frame = ttk.Frame(self.history_frame, padding="5")
        self.history_buttons_frame.grid(row=1, column=0, sticky="ew")
        self.history_buttons_frame.grid_columnconfigure(0, weight=1)
        self.history_buttons_frame.grid_columnconfigure(1, weight=1)
        self.history_buttons_frame.grid_columnconfigure(2, weight=1)

        self.save_request_button = ttk.Button(self.history_buttons_frame, text="Save Current Request", command=self._save_current_request, bootstyle="success")
        self.save_request_button.grid(row=0, column=0, sticky="ew", padx=2, pady=5)

        self.load_request_button = ttk.Button(self.history_buttons_frame, text="Load Selected", command=self._load_selected_request, bootstyle="info")
        self.load_request_button.grid(row=0, column=1, sticky="ew", padx=2, pady=5)

        self.delete_request_button = ttk.Button(self.history_buttons_frame, text="Delete Selected", command=self._delete_selected_request, bootstyle="danger")
        self.delete_request_button.grid(row=0, column=2, sticky="ew", padx=2, pady=5)

        self.export_buttons_frame = ttk.Frame(self.response_tab)
        self.export_buttons_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        self.export_json_button = ttk.Button(self.export_buttons_frame, text="Export JSON", command=self._export_response_json, bootstyle="success")
        self.export_json_button.grid(row=0, column=0, sticky="ew", padx=2)

        self.export_csv_button = ttk.Button(self.export_buttons_frame, text="Export CSV", command=self._export_response_csv, bootstyle="info")
        self.export_csv_button.grid(row=0, column=1, sticky="ew", padx=2)

        self.export_json_button.config(state=tk.DISABLED)
        self.export_csv_button.config(state=tk.DISABLED)


    def _load_requests_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []

    def _save_requests_history(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.saved_requests, f, indent=4)

    def _populate_history_listbox(self):
        self.history_listbox.delete(0, tk.END)
        for idx, req in enumerate(self.saved_requests):
            display_text = f"{req.get('method', 'N/A')} {req.get('url', 'N/A')}"
            self.history_listbox.insert(tk.END, display_text)

    def _on_history_select(self, event):
        selected_indices = self.history_listbox.curselection()
        if selected_indices:
            idx = selected_indices[0]
            request_data = self.saved_requests[idx]
            self._update_status(f"Selected: {request_data.get('method')} {request_data.get('url')}", bootstyle="info")

    def _save_current_request(self):
        req_data = {
            "method": self.method_combobox.get(),
            "url": self.url_entry.get(),
            "headers": self.headers_text.get(1.0, tk.END).strip(),
            "query_params": self.query_params_text.get(1.0, tk.END).strip(),
            "body_type": self.body_type_combobox.get(),
            "body": self.body_text.get(1.0, tk.END).strip(),
            "auth_username": self.auth_username_entry.get(),
            "auth_password": self.auth_password_entry.get()
        }
        self.saved_requests.append(req_data)
        self._save_requests_history()
        self._populate_history_listbox()
        self._update_status("Current request saved.", bootstyle="success")

    def _load_selected_request(self):
        selected_indices = self.history_listbox.curselection()
        if selected_indices:
            idx = selected_indices[0]
            request_data = self.saved_requests[idx]

            self.method_combobox.set(request_data.get("method", "GET"))
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, request_data.get("url", ""))
            self.headers_text.delete(1.0, tk.END)
            self.headers_text.insert(tk.END, request_data.get("headers", ""))
            self.query_params_text.delete(1.0, tk.END)
            self.query_params_text.insert(tk.END, request_data.get("query_params", ""))
            self.body_type_combobox.set(request_data.get("body_type", "Raw (JSON)"))
            self.body_text.delete(1.0, tk.END)
            self.body_text.insert(tk.END, request_data.get("body", ""))
            self.auth_username_entry.delete(0, tk.END)
            self.auth_username_entry.insert(0, request_data.get("auth_username", ""))
            self.auth_password_entry.delete(0, tk.END)
            self.auth_password_entry.insert(0, request_data.get("auth_password", ""))

            self._update_status("Selected request loaded.", bootstyle="info")
        else:
            messagebox.showwarning("Load Request", "Please select a request to load from history.")
            self._update_status("No request selected for loading.", bootstyle="warning")

    def _delete_selected_request(self):
        selected_indices = self.history_listbox.curselection()
        if selected_indices:
            idx = selected_indices[0]
            del self.saved_requests[idx]
            self._save_requests_history()
            self._populate_history_listbox()
            self._update_status("Selected request deleted.", bootstyle="success")
        else:
            messagebox.showwarning("Delete Request", "Please select a request to delete from history.")
            self._update_status("No request selected for deletion.", bootstyle="warning")

    def _update_status(self, message, bootstyle="secondary"):
        self.status_bar.config(text=message, bootstyle=bootstyle)
        self.root.update_idletasks()

    def _copy_to_clipboard(self, text_content):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text_content.strip())
            self.root.update()
            self._update_status("Content copied to clipboard!", bootstyle="success")
        except Exception as e:
            messagebox.showerror("Clipboard Error", f"Failed to copy to clipboard: {e}")
            self._update_status("Failed to copy to clipboard.", bootstyle="danger")

    def _clear_response_fields(self):
        self.status_label.config(text="N/A", bootstyle="secondary")
        self.response_headers_text.config(state=tk.NORMAL)
        self.response_headers_text.delete(1.0, tk.END)
        self.response_headers_text.config(state=tk.DISABLED)
        self.response_body_text.config(state=tk.NORMAL)
        self.response_body_text.delete(1.0, tk.END)
        self.response_body_text.config(state=tk.DISABLED)
        self.export_json_button.config(state=tk.DISABLED)
        self.export_csv_button.config(state=tk.DISABLED)
        self._last_response_json = None

        self._update_status("Response fields cleared.", bootstyle="info")

    def _export_response_json(self):
        if self._last_response_json is None:
            messagebox.showwarning("Export JSON", "No JSON response to export.")
            self._update_status("No JSON response to export.", bootstyle="warning")
            return

        try:
            with open("response.json", "w") as f:
                json.dump(self._last_response_json, f, indent=4)
            self._update_status("Response exported to response.json", bootstyle="success")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export JSON: {e}")
            self._update_status(f"Failed to export JSON: {e}", bootstyle="danger")
    def _export_response_csv(self):
        if self._last_response_json is None:
            messagebox.showwarning("Export CSV", "No JSON response to export.")
            self._update_status("No JSON response to export.", bootstyle="warning")
            return

        try:
            import pandas as pd
            df = pd.json_normalize(self._last_response_json)
            df.to_csv("response.csv", index=False)
            self._update_status("Response exported to response.csv", bootstyle="success")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV: {e}")
            self._update_status(f"Failed to export CSV: {e}", bootstyle="danger")

    def _update_status(self, message, bootstyle="secondary"):
        self.status_bar.config(text=message, bootstyle=bootstyle)
        self.root.update_idletasks()


    def _parse_key_value_text(self, raw_text):
        parsed_dict = {}
        for line in raw_text.splitlines():
            line = line.strip()
            if line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    parsed_dict[key] = value
                else:
                    self._update_status(f"Skipping malformed line: '{line}'. Expected 'Key: Value'.", bootstyle="warning")
        return parsed_dict

    def _fetch_virtualstock_orders(self):
        from requests.auth import HTTPBasicAuth

        api_url = "https://api.virtualstock.com/restapi/v4/orders/"
        username = "your_username"
        password = "your_password"

        params = {
            "limit": 5,
            "offset": 0,
            "status": "ORDER"
        }
        headers = {
            "Accept": "application/json"
        }

        self.orders_output.delete(1.0, tk.END)
        self._update_status("Fetching Virtualstock orders...", bootstyle="info")

        try:
            response = requests.get(api_url, params=params, auth=HTTPBasicAuth(username, password), headers=headers, timeout=15)
            response.raise_for_status()
            orders = response.json().get("orders", [])

            if not orders:
                self.orders_output.insert(tk.END, "No new orders found.")
                self._update_status("No orders found.", bootstyle="warning")
                return

            formatted = json.dumps(orders, indent=2)
            self.orders_output.insert(tk.END, formatted)
            self._update_status(f"Fetched {len(orders)} orders.", bootstyle="success")

        except requests.exceptions.RequestException as e:
            self.orders_output.insert(tk.END, f"Error fetching orders:\n{e}")
            self._update_status("Failed to fetch orders.", bootstyle="danger")



    def _change_theme(self, event):
        selected_theme = self.theme_combobox.get()
        self.style.theme_use(selected_theme)
        self._update_status(f"Theme changed to {selected_theme}", bootstyle="info")




    def cancel_request(self):
        self.send_button.config(state=tk.NORMAL)
        self.export_json_button.config(state=tk.DISABLED)
        self.export_csv_button.config(state=tk.DISABLED)
        self._clear_response_fields()
        self._last_response_json = None
        self._update_status("Request cancelled.", bootstyle="warning")

    def send_request(self):
        self._clear_response_fields()
        self._update_status("Sending request...", bootstyle="info")
        self.send_button.config(state=tk.DISABLED)
        self.export_json_button.config(state=tk.NORMAL)
        self.export_csv_button.config(state=tk.NORMAL)
        self._last_response_json = None

        method = self.method_combobox.get()
        url = self.url_entry.get()
        headers_raw = self.headers_text.get(1.0, tk.END).strip()
        body_type = self.body_type_combobox.get()
        request_body_raw = self.body_text.get(1.0, tk.END).strip()

        if not url:
            messagebox.showerror("Error", "URL cannot be empty.")
            self._update_status("Error: URL cannot be empty.", bootstyle="danger")
            self.send_button.config(state=tk.NORMAL)
            return

        headers = self._parse_key_value_text(headers_raw)
        query_params = self._parse_key_value_text(self.query_params_text.get(1.0, tk.END).strip())

        request_data = None
        json_data = None

        if method in ["POST", "PUT", "PATCH"]:
            if body_type == "Raw (JSON)":
                if request_body_raw:
                    try:
                        json_data = json.loads(request_body_raw)
                    except json.JSONDecodeError as e:
                        messagebox.showerror("JSON Error", f"Invalid JSON in request body: {e}")
                        self._update_status("Error: Invalid JSON in request body.", bootstyle="danger")
                        self.send_button.config(state=tk.NORMAL)
                        return
                else:
                    json_data = {}
            elif body_type == "Form Data (x-www-form-urlencoded)":
                request_data = request_body_raw
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/x-www-form-urlencoded"
            elif body_type == "None":
                request_data = None
                json_data = None
            else:
                request_data = request_body_raw

        auth_username = self.auth_username_entry.get()
        auth_password = self.auth_password_entry.get()
        auth_tuple = (auth_username, auth_password) if auth_username or auth_password else None

        try:
            timeout_val = self.timeout_var.get()
            follow_redirects_val = self.follow_redirects_var.get()
            ssl_verify_val = self.ssl_verify_var.get()

            response = requests.request(
                method,
                url,
                headers=headers, # Headers should be a dictionary
                # If you want to send headers as a list of tuples, use headers=[('Key', 'Value')]
                # If you want to send headers as a dictionary, use headers={'Key': 'Value'}
                params=query_params,
                json=json_data, # Use json for JSON body, data for form data
                # If you want to send a raw string body, use data=request_body_raw
                # If you want to send a file, use files={'file': open('filename', 'rb')}
                # If you want to send a multipart form data, use files={'file': ('filename', open('filename', 'rb'), 'application/octet-stream')}
                # If you want to send a file with a specific content type, use files={'file': ('filename', open('filename', 'rb'), 'application/json')}
                # If you want to send a file with a specific content type, use files={'file': ('filename', open('filename', 'rb'), 'application/x-www-form-urlencoded')}
                # If you want to send a file with a specific content type, use files={'file': ('filename', open('filename', 'rb'), 'text/plain')}
                data=request_data, # Use json for JSON body, data for form data
                # If you want to send a raw string body, use data=request_body_raw
                # If you want to send a file, use files={'file': open('filename', 'rb')}
                # If you want to send a multipart form data, use files={'file': ('filename', open('filename', 'rb'), 'application/octet-stream')}
                # If you want to send a file with a specific content type, use files={'file': ('filename', open('filename', 'rb'), 'application/json')}
                # If you want to send a file with a specific content type, use files={'file': ('filename', open('filename', 'rb'), 'application/x-www-form-urlencoded')}
                # If you want to send a file with a specific content type, use files={'file': ('filename', open('filename', 'rb'), 'text/plain')}
                # If you want to send a file with a specific content type, use files={'file': ('filename', open('filename', 'rb'), 'application/octet-stream')}

                auth=auth_tuple,
                timeout=timeout_val, # Timeout for the request
                # If you want to disable timeout, set this to None
                # If you want to set a custom timeout, set this to a float value (e.g., 5.0 for 5 seconds)
                # If you want to set a tuple for connect and read timeouts, use (connect_timeout, read_timeout)
                # e.g., (5.0, 10.0) for 5 seconds
                # If you want to set a custom timeout for connect and read, use a tuple like (connect_timeout, read_timeout)
                # e.g., (5.0, 10.0) for 5 seconds

                allow_redirects=follow_redirects_val,
                verify=ssl_verify_val   # This is the SSL verification setting
                # If you want to disable SSL verification, set this to False

            )

            self.status_label.config(text=f"{response.status_code} {response.reason}",
                                     bootstyle="success" if response.ok else "danger")
            self._update_status(f"Request completed: {response.status_code} {response.reason}",
                                bootstyle="success" if response.ok else "danger")

            # Set _last_response_json after response is available
            if 'application/json' in response.headers.get('Content-Type', '').lower():
                try:
                    self._last_response_json = response.json()
                except Exception:
                    self._last_response_json = None
            else:
                self._last_response_json = None

            self.response_headers_text.config(state=tk.NORMAL)
            self.response_headers_text.delete(1.0, tk.END)
            for key, value in response.headers.items():
                self.response_headers_text.insert(tk.END, f"{key}: {value}\n")
            self.response_headers_text.config(state=tk.DISABLED)

            self.response_body_text.config(state=tk.NORMAL)
            self.response_body_text.delete(1.0, tk.END)
            try:
                if 'application/json' in response.headers.get('Content-Type', '').lower():
                    pretty_json = json.dumps(response.json(), indent=2)
                    self.response_body_text.insert(tk.END, pretty_json)
                else:
                    self.response_body_text.insert(tk.END, response.text)
            except json.JSONDecodeError:
                self.response_body_text.insert(tk.END, response.text)
            self.response_body_text.config(state=tk.DISABLED)

        except requests.exceptions.Timeout:
            messagebox.showerror("Request Error", "The request timed out.")
            self._update_status("Error: Request timed out.", bootstyle="danger")
            self.status_label.config(text="Timeout Error", bootstyle="danger")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Request Error", "Could not connect to the server. Check URL or internet connection.")
            self._update_status("Error: Connection failed.", bootstyle="danger")
            self.status_label.config(text="Connection Error", bootstyle="danger")
        except requests.exceptions.HTTPError as e:
            messagebox.showerror("HTTP Error", f"HTTP error occurred: {e}")
            self._update_status(f"Error: HTTP {e.response.status_code}", bootstyle="danger")
            self.status_label.config(text=f"HTTP Error: {e.response.status_code}", bootstyle="danger")
            if e.response:
                self.response_headers_text.config(state=tk.NORMAL)
                self.response_headers_text.delete(1.0, tk.END)
                for key, value in e.response.headers.items():
                    self.response_headers_text.insert(tk.END, f"{key}: {value}\n")
                self.response_headers_text.config(state=tk.DISABLED)

                self.response_body_text.config(state=tk.NORMAL)
                self.response_body_text.delete(1.0, tk.END)
                try:
                    if 'application/json' in e.response.headers.get('Content-Type', '').lower():
                        pretty_json = json.dumps(e.response.json(), indent=2)
                        self.response_body_text.insert(tk.END, pretty_json)
                    else:
                        self.response_body_text.insert(tk.END, e.response.text)
                except json.JSONDecodeError:
                    self.response_body_text.insert(tk.END, e.response.text)
                self.response_body_text.config(state=tk.DISABLED)

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Request Error", f"An unexpected error occurred: {e}")
            self._update_status("Error: An unexpected request error occurred.", bootstyle="danger")
            self.status_label.config(text="Request Error", bootstyle="danger")
        finally:
            self.send_button.config(state=tk.NORMAL)
            self.export_json_button.config(state=tk.NORMAL if self._last_response_json else tk.DISABLED)
            self.export_csv_button.config(state=tk.NORMAL if self._last_response_json else tk.DISABLED)

if __name__ == "__main__":
    style = Style(theme="superhero")
    root = style.master
    app = ApiClientApp(root)
    root.mainloop()
