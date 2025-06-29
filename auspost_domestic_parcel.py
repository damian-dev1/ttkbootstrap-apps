
import csv
import requests
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, filedialog

API_KEY = "YOUR_API_KEY"
API_URL = "https://digitalapi.auspost.com.au/postage/parcel/domestic"

SERVICE_OPTIONS = {
    "AUS_PARCEL_EXPRESS": [
        "AUS_PARCEL_EXPRESS_SATCHEL_SMALL",
        "AUS_PARCEL_EXPRESS_PACKAGE_SMALL",
        "AUS_PARCEL_EXPRESS_SATCHEL_500G"
    ],
    "AUS_PARCEL_REGULAR": [
        "AUS_PARCEL_REGULAR_SATCHEL_SMALL",
        "AUS_PARCEL_REGULAR_PACKAGE_SMALL",
        "AUS_PARCEL_REGULAR_SATCHEL_500G"
    ]
}

class PostageCalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Postage Calculator")
        self.history = []

        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=True)

        ttk.Label(main_frame, text="Postage Calculator", font=("Segoe UI", 16, "bold")).pack(pady=10)

        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=X)

        self.fields = {}
        labels = [
            ("From Postcode:*", "from_postcode"),
            ("To Postcode:*", "to_postcode"),
            ("Length (cm):*", "length"),
            ("Width (cm):*", "width"),
            ("Height (cm):*", "height"),
            ("Weight (kg):*", "weight")
        ]

        for label, key in labels:
            ttk.Label(form_frame, text=label).pack(anchor=W, pady=(10, 0))
            entry = ttk.Entry(form_frame)
            entry.pack(fill=X)
            self.fields[key] = entry

        ttk.Label(form_frame, text="Service Code:*").pack(anchor=W, pady=(10, 0))
        self.service_code = ttk.Combobox(form_frame, state="readonly")
        self.service_code["values"] = list(SERVICE_OPTIONS.keys())
        self.service_code.pack(fill=X)
        self.service_code.bind("<<ComboboxSelected>>", self.update_suboptions)

        ttk.Label(form_frame, text="Suboption Code:").pack(anchor=W, pady=(10, 0))
        self.suboption_code = ttk.Combobox(form_frame, state="readonly")
        self.suboption_code.pack(fill=X)

        ttk.Button(form_frame, text="Calculate Postage", command=self.calculate_postage, bootstyle=PRIMARY).pack(pady=15)

        ttk.Label(main_frame, text="Calculation History:").pack(anchor=W, pady=(10, 0))
        self.history_box = ttk.Text(main_frame, height=10)
        self.history_box.pack(fill=BOTH, expand=True)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Clear History", command=self.clear_history, bootstyle=PRIMARY).pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="Export to CSV", command=self.export_csv, bootstyle=PRIMARY).pack(side=LEFT, padx=5)

    def update_suboptions(self, event=None):
        selected = self.service_code.get()
        self.suboption_code["values"] = SERVICE_OPTIONS.get(selected, [])
        if self.suboption_code["values"]:
            self.suboption_code.set(self.suboption_code["values"][0])

    def calculate_postage(self):
        headers = {"AUTH-KEY": API_KEY}
        try:
            payload = {
                "from_postcode": self.fields["from_postcode"].get(),
                "to_postcode": self.fields["to_postcode"].get(),
                "length": self.fields["length"].get(),
                "width": self.fields["width"].get(),
                "height": self.fields["height"].get(),
                "weight": str(float(self.fields["weight"].get()) * 1000),  # kg to g
                "service_code": self.service_code.get()
            }
        except Exception:
            messagebox.showerror("Error", "Invalid input. Please check your values.")
            return

        if not all(payload.values()):
            messagebox.showwarning("Validation Error", "Please fill in all required fields.")
            return

        if self.suboption_code.get():
            payload["suboption_code"] = self.suboption_code.get()

        try:
            r = requests.get(API_URL, headers=headers, params=payload)
            r.raise_for_status()
            data = r.json()["postage_result"]
            result_str = f"${data['total_cost']} | {data.get('delivery_time', 'No ETA')}"
            self.history.append(payload | {"cost": data["total_cost"], "eta": data.get("delivery_time", "")})
            self.history_box.insert("end", result_str + "\n")
        except Exception as e:
            messagebox.showerror("API Error", str(e))

    def clear_history(self):
        self.history.clear()
        self.history_box.delete("1.0", "end")

    def export_csv(self):
        if not self.history:
            messagebox.showinfo("Export", "No history to export.")
            return
        f = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not f:
            return
        keys = ["from_postcode", "to_postcode", "length", "width", "height", "weight", "service_code", "suboption_code", "cost", "eta"]
        with open(f, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.history)
        messagebox.showinfo("Export", "Export complete.")

if __name__ == "__main__":
    app = ttk.Window(themename="cyborg")
    PostageCalculatorApp(app)
    app.mainloop()
