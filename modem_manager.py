import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
from tkinter import messagebox
import serial.tools.list_ports
from modem import Modem
import commands


class ModemManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📡 Modem Manager - RG500Q")
        self.modem = None

        self.port_var = ttk.StringVar()
        self.apn_var = ttk.StringVar(value="yesinternet")

        self.build_ui()

    def build_ui(self):
        port_frame = ttk.LabelFrame(self.root, text="Serial Port", padding=10)
        port_frame.pack(fill=X, padx=10, pady=5)

        ports = [p.device for p in serial.tools.list_ports.comports()]
        ttk.Label(port_frame, text="Port:").pack(side=LEFT, padx=5)
        self.port_menu = ttk.Combobox(port_frame, textvariable=self.port_var, values=ports, width=20)
        self.port_menu.pack(side=LEFT, padx=5)
        ttk.Button(port_frame, text="🔄 Refresh", command=self.refresh_ports, bootstyle=INFO).pack(side=LEFT, padx=5)
        ttk.Button(port_frame, text="🔌 Connect", command=self.connect_modem, bootstyle=SUCCESS).pack(side=LEFT, padx=5)
        ttk.Button(port_frame, text="❌ Disconnect", command=self.disconnect_modem, bootstyle=DANGER).pack(side=LEFT, padx=5)

        apn_frame = ttk.LabelFrame(self.root, text="APN Configuration", padding=10)
        apn_frame.pack(fill=X, padx=10, pady=5)

        ttk.Label(apn_frame, text="APN:").pack(side=LEFT, padx=5)
        ttk.Entry(apn_frame, textvariable=self.apn_var, width=30).pack(side=LEFT, padx=5)
        ttk.Button(apn_frame, text="🌐 Set APN & Connect", command=self.setup_apn, bootstyle=PRIMARY).pack(side=LEFT, padx=5)

        action_frame = ttk.Frame(self.root, padding=10)
        action_frame.pack(fill=X, padx=10, pady=5)

        ttk.Button(action_frame, text="📶 Signal", command=self.get_signal, bootstyle=SECONDARY).pack(side=LEFT, padx=5)
        ttk.Button(action_frame, text="🏢 Operator", command=self.get_operator, bootstyle=SECONDARY).pack(side=LEFT, padx=5)
        ttk.Button(action_frame, text="🌍 Get IP", command=self.get_ip, bootstyle=SECONDARY).pack(side=LEFT, padx=5)
        ttk.Button(action_frame, text="📋 Full Status", command=self.full_status, bootstyle=WARNING).pack(side=LEFT, padx=5)

        console_frame = ttk.LabelFrame(self.root, text="Console Output", padding=10)
        console_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        self.console = ScrolledText(console_frame, wrap="word", height=18, font=("Courier New", 10))
        self.console.pack(fill=BOTH, expand=True)

    def log(self, message):
        self.console.insert("end", message + "\n")
        self.console.see("end")

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_var.set("")
        self.port_menu.configure(values=ports)

    def connect_modem(self):
        try:
            self.modem = Modem(port=self.port_var.get())
            self.modem.connect()
            self.log(f"[INFO] Connected to {self.port_var.get()}")
        except Exception as e:
            messagebox.showerror("Connection Failed", str(e))

    def disconnect_modem(self):
        if self.modem:
            self.modem.disconnect()
            self.modem = None
            self.log("[INFO] Disconnected")

    def setup_apn(self):
        if not self.modem:
            messagebox.showwarning("Not Connected", "Connect to modem first.")
            return
        apn = self.apn_var.get().strip()
        self.log("[ACTION] Setting APN...")
        self.log("\n".join(commands.setup_apn(self.modem, apn)))
        self.log("[ACTION] Activating PDP...")
        self.log("\n".join(commands.activate_pdp(self.modem)))
        self.log("[ACTION] Getting IP...")
        self.log("\n".join(commands.get_ip_address(self.modem)))

    def get_signal(self):
        if self.modem:
            self.log("[ACTION] Signal Quality:")
            self.log("\n".join(commands.check_signal(self.modem)))

    def get_operator(self):
        if self.modem:
            self.log("[ACTION] Current Operator:")
            self.log("\n".join(commands.get_operator(self.modem)))

    def get_ip(self):
        if self.modem:
            self.log("[ACTION] IP Address:")
            self.log("\n".join(commands.get_ip_address(self.modem)))

    def full_status(self):
        if self.modem:
            self.log("[ACTION] Full Modem Status:")
            report = commands.full_status_report(self.modem)
            for key, val in report.items():
                self.log(f"[{key}]\n" + "\n".join(val))


def launch_gui():
    app = ttk.Window(themename="cyborg", title="Modem Manager", size=(800, 600))
    ModemManagerApp(app)
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
