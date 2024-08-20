import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import aiohttp
import asyncio
import time
import threading

class DownloadApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CDN下行软件_XiaoLiu")
        self.root.geometry("400x350")
        self.root.configure(bg="#f0f0f0")

        self.frame = ttk.Frame(self.root, padding="10")
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.label = ttk.Label(self.frame, text="并发连接数-推荐1~512", font=("Helvetica", 12))
        self.label.grid(row=0, column=0, sticky=tk.W, pady=5)

        self.entry = ttk.Entry(self.frame, width=20)
        self.entry.grid(row=0, column=1, pady=5)

        self.url_button = ttk.Button(self.frame, text="设置地址", command=self.set_url)
        self.url_button.grid(row=1, column=0, columnspan=2, pady=5)

        self.max_limit_label = ttk.Label(self.frame, text="最大使用量 (GB)", font=("Helvetica", 12))
        self.max_limit_label.grid(row=2, column=0, sticky=tk.W, pady=5)

        self.max_limit_entry = ttk.Entry(self.frame, width=20)
        self.max_limit_entry.grid(row=2, column=1, pady=5)

        self.start_button = ttk.Button(self.frame, text="开始", command=self.start_download)
        self.start_button.grid(row=3, column=0, columnspan=2, pady=5)

        self.status_label = ttk.Label(self.frame, text="状态: 未开始", font=("Helvetica", 12))
        self.status_label.grid(row=4, column=0, columnspan=2, pady=5)

        self.progress = ttk.Progressbar(self.frame, orient="horizontal", length=300, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=2, pady=5)

        self.speed_label = ttk.Label(self.frame, text="下载速度: 0 MB/s", font=("Helvetica", 12))
        self.speed_label.grid(row=6, column=0, columnspan=2, pady=5)

        self.data_label = ttk.Label(self.frame, text="已下载: 0 MB", font=("Helvetica", 12))
        self.data_label.grid(row=7, column=0, columnspan=2, pady=5)

        self.default_url = 'https://dn-lego-static.qbox.me/1719901769-2024_mkt_m7_banner.png'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 666.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110'
        }
        self.total_data_received = 0
        self.start_time = None
        self.limit_enabled = False
        self.max_limit = 0
        self.url = self.default_url
        self.downloading = False
        self.loop = None
        self.last_update_time = None
        self.last_data_received = 0

    def set_url(self):
        dialog = UrlDialog(self.root, self.default_url)
        self.root.wait_window(dialog.top)
        if dialog.result:
            self.url = dialog.result
        else:
            self.url = self.default_url

    def start_download(self):
        try:
            connections = int(self.entry.get())
            if connections <= 0:
                raise ValueError("并发连接数必须大于0")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            return

        max_limit_gb = self.max_limit_entry.get()
        if max_limit_gb.strip() and float(max_limit_gb) > 0:
            self.limit_enabled = True
            self.max_limit = float(max_limit_gb) * 1024 * 1024 * 1024
        else:
            self.limit_enabled = False
        self.start_time = time.time()
        self.status_label.config(text="状态: 工作中")
        self.downloading = True
        self.total_data_received = 0
        self.last_update_time = self.start_time
        self.last_data_received = 0
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.run_async_loop, args=(connections,), daemon=True).start()
        self.update_status()

    def run_async_loop(self, connections):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.download(connections))

    async def download(self, connections):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            tasks = [self.send_get_request(session) for _ in range(connections)]
            await asyncio.gather(*tasks)
        self.downloading = False
        self.loop.call_soon_threadsafe(self.update_status)

    async def send_get_request(self, session):
        while self.downloading:
            if self.limit_enabled and self.total_data_received >= self.max_limit:
                break
            try:
                async with session.get(self.url) as response:
                    if response.status == 200:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            data_length = len(chunk)
                            self.total_data_received += data_length
                            if self.limit_enabled and self.total_data_received >= self.max_limit:
                                break
            except aiohttp.ClientError as e:
                messagebox.showerror("错误", f"下载失败: {e}")
                self.downloading = False
                break
            await asyncio.sleep(0.1)  # Add a small delay to reduce CPU usage

    def update_status(self):
        if self.start_time is not None:
            current_time = time.time()
            elapsed_time = current_time - self.start_time
            total_data_received_mb = self.total_data_received / (1024 * 1024)
            speed_mbps = (self.total_data_received - self.last_data_received) / ((current_time - self.last_update_time) * 1024 * 1024) if current_time > self.last_update_time else 0

            self.speed_label.config(text=f"下载速度: {speed_mbps:.2f} MB/s")
            self.data_label.config(text=f"已下载: {total_data_received_mb:.2f} MB")

            if self.limit_enabled:
                progress_percentage = (self.total_data_received / self.max_limit) * 100
                self.progress['value'] = progress_percentage

            self.status_label.config(text=f"状态: 下载中 - {speed_mbps:.2f} MB/s")

            self.last_update_time = current_time
            self.last_data_received = self.total_data_received

        if self.downloading:
            self.root.after(1000, self.update_status)  # Update status every second
        else:
            self.status_label.config(text="状态: 下载完成")

class UrlDialog:
    def __init__(self, parent, default_url):
        top = self.top = tk.Toplevel(parent)
        top.geometry("400x100")
        top.configure(bg="#f0f0f0")
        self.label = ttk.Label(top, text="请输入刷流网站地址:", font=("Helvetica", 12))
        self.label.pack(pady=5)
        self.entry = ttk.Entry(top, width=40)
        self.entry.insert(0, default_url)
        self.entry.pack(pady=5)
        self.ok_button = ttk.Button(top, text="确定", command=self.ok)
        self.ok_button.pack(pady=5)
        self.result = None

    def ok(self):
        self.result = self.entry.get()
        self.top.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DownloadApp(root)
    root.mainloop()