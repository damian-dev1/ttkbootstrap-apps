import asyncio
import httpx
import pandas as pd
import time
import threading
import logging
from pathlib import Path
from config import API_KEY
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, END

logging.basicConfig(level=logging.INFO)

class FreightRateChecker:
    def __init__(self, api_key=API_KEY):
        self.api_key = api_key
        self.url = "https://"
        self.headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }

    async def check_freight_rates(self, product_code, post_code):
        payload = [{"productCode": product_code, "postCode": post_code}]
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(self.url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            if data[0]['deliveryPossible']:
                return {
                    "success": True,
                    "rate": data[0]['deliveryRate']
                }
            else:
                return {"success": False}

class FreightRateBulkChecker:
    def __init__(self, api_key=API_KEY, rate_limit_per_minute=100):
        self.api_key = api_key
        self.url = "https://api.digital.messagepool.com/soh/dropship"
        self.headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
        self.rate_limit = asyncio.Semaphore(rate_limit_per_minute)
        self.last_reset = time.time()
        self.calls_made = 0
        self.rate_limit_per_minute = rate_limit_per_minute

    def create_excel_template(self, save_path="freight_rate_template.xlsx"):
        df = pd.DataFrame(columns=["SKU", "PostCode"])
        df.to_excel(save_path, index=False)
        return Path(save_path).absolute()

    async def _check_one(self, client, sku, post_code):
        await self._enforce_rate_limit()
        payload = [{"productCode": sku, "postCode": post_code}]
        try:
            response = await client.post(self.url, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data[0]['deliveryPossible']:
                return {
                    "SKU": sku,
                    "PostCode": post_code,
                    "Rate": data[0]['deliveryRate'],
                    "Status": "OK"
                }
            else:
                return {
                    "SKU": sku,
                    "PostCode": post_code,
                    "Rate": None,
                    "Status": "Not Found"
                }
        except Exception as e:
            return {
                "SKU": sku,
                "PostCode": post_code,
                "Rate": None,
                "Status": f"Error: {str(e)}"
            }

    async def _enforce_rate_limit(self):
        async with self.rate_limit:
            now = time.time()
            if now - self.last_reset >= 60:
                self.calls_made = 0
                self.last_reset = now
            elif self.calls_made >= self.rate_limit_per_minute:
                sleep_time = 60 - (now - self.last_reset)
                await asyncio.sleep(sleep_time)
                self.calls_made = 0
                self.last_reset = time.time()
            self.calls_made += 1

    async def run_bulk_check(self, excel_path, output_path="freight_rate_results.xlsx"):
        df = pd.read_excel(excel_path)
        tasks = []
        async with httpx.AsyncClient(verify=False) as client:
            for _, row in df.iterrows():
                sku = str(row["SKU"]).strip()
                post_code = str(row["PostCode"]).strip()
                tasks.append(self._check_one(client, sku, post_code))
            results = await asyncio.gather(*tasks)
        results_df = pd.DataFrame(results)
        results_df.to_excel(output_path, index=False)
        return Path(output_path).absolute()

class FreightRateCheckerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Freight Matrix Rate Checker")
        self.checker = FreightRateChecker()
        self.bulk_checker = FreightRateBulkChecker()
        self.bulk_input_path = None

        self.product_code_var = ttk.StringVar()
        self.post_code_var = ttk.StringVar()
        self.result_var = ttk.StringVar(value="Result will appear here...")

        container = ttk.Frame(self.root, padding=20)
        container.pack(fill=BOTH, expand=True)

        single = ttk.Labelframe(container, text="Single Rate Check", padding=15)
        single.pack(fill=X, pady=10)

        ttk.Label(single, text="SKU").grid(row=0, column=0, sticky=W, pady=5)
        ttk.Entry(single, textvariable=self.product_code_var, width=30).grid(row=0, column=1, pady=5)

        ttk.Label(single, text="Post Code").grid(row=1, column=0, sticky=W, pady=5)
        ttk.Entry(single, textvariable=self.post_code_var, width=30).grid(row=1, column=1, pady=5)

        ttk.Button(single, text="Check Rate", command=self.run_async_check, bootstyle=SUCCESS).grid(row=2, column=0, columnspan=2, pady=10)

        self.result_label = ttk.Label(single, textvariable=self.result_var, font=("Segoe UI", 11), wraplength=400)
        self.result_label.grid(row=3, column=0, columnspan=2, pady=5)

        bulk = ttk.Labelframe(container, text="Bulk Rate Check via Excel", padding=15)
        bulk.pack(fill=X, pady=10)

        ttk.Button(bulk, text="⬇ Download Template", command=self.download_template, bootstyle=INFO).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(bulk, text="📤 Upload and Run", command=self.upload_and_run_bulk, bootstyle=WARNING).grid(row=0, column=1, padx=5, pady=5)

        self.log_output = ttk.ScrolledText(container, height=12, wrap="word")
        self.log_output.pack(fill=BOTH, expand=True, pady=(10, 0))

    def log(self, msg):
        self.log_output.insert(END, msg + '\n')
        self.log_output.see(END)

    def run_async_check(self):
        threading.Thread(target=self._run_async_check_wrapper, daemon=True).start()

    def _run_async_check_wrapper(self):
        asyncio.run(self._fetch_rate())

    async def _fetch_rate(self):
        product_code = self.product_code_var.get().strip()
        post_code = self.post_code_var.get().strip()
        if not product_code or not post_code:
            self.log("⚠️ Please enter both SKU and Post Code.")
            return
        try:
            result = await self.checker.check_freight_rates(product_code, post_code)
            if result["success"]:
                self.result_label.configure(bootstyle=SUCCESS)
                self.result_var.set(f"✅ Rate: ${result['rate']}")
                self.log(f"✅ {product_code} → {post_code} = ${result['rate']}")
            else:
                self.result_label.configure(bootstyle=DANGER)
                self.result_var.set("❌ Not found.")
                self.log(f"❌ No rate found for {product_code} to {post_code}.")
        except Exception as e:
            self.log(f"❌ API Error: {e}")

    def download_template(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", title="Save Template As", initialfile="freight_rate_template.xlsx")
        if path:
            saved = self.bulk_checker.create_excel_template(path)
            self.log(f"✅ Template saved to: {saved}")

    def upload_and_run_bulk(self):
        in_path = filedialog.askopenfilename(title="Select Excel File", filetypes=[("Excel Files", "*.xlsx")])
        if not in_path:
            self.log("⚠️ No file selected.")
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".xlsx", title="Save Results As", initialfile="freight_results.xlsx")
        if not out_path:
            self.log("⚠️ No output file specified.")
            return
        threading.Thread(target=lambda: asyncio.run(self._run_bulk(in_path, out_path)), daemon=True).start()

    async def _run_bulk(self, in_path, out_path):
        try:
            self.log(f"⏳ Processing file: {in_path}")
            result = await self.bulk_checker.run_bulk_check(in_path, out_path)
            self.log(f"✅ Results saved to: {result}")
        except Exception as e:
            self.log(f"❌ Bulk check failed: {e}")

if __name__ == "__main__":
    app = ttk.Window(themename="cyborg")
    FreightRateCheckerUI(app)
    app.mainloop()
