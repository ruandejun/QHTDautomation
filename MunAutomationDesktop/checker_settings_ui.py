"""
Tkinter / Custom UI Dialog để cấu hình API Key & Thông số Checker
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys

from sadcaptcha_solver import load_settings, save_settings


class CheckerSettingsDialog(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("⚙️ Cấu hình Checker & Giải Captcha")
        self.geometry("520x360")
        self.resizable(False, False)
        self.configure(bg="#0f172a")

        self.settings = load_settings()
        self.init_ui()

    def init_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Container
        container = tk.Frame(self, bg="#0f172a", padx=20, pady=20)
        container.pack(fill="both", expand=True)

        # Title
        lbl_title = tk.Label(
            container,
            text="Cấu hình Dịch vụ & SadCaptcha API",
            font=("Segoe UI", 12, "bold"),
            bg="#0f172a",
            fg="#38bdf8"
        )
        lbl_title.pack(anchor="w", pady=(0, 15))

        # 1. API Key
        lbl_key = tk.Label(container, text="SadCaptcha API Key:", font=("Segoe UI", 10), bg="#0f172a", fg="#f1f5f9")
        lbl_key.pack(anchor="w")
        self.entry_key = tk.Entry(container, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", insertbackground="#38bdf8", relief="flat", highlightthickness=1, highlightbackground="#334155")
        self.entry_key.pack(fill="x", pady=(5, 12), ipady=4)
        self.entry_key.insert(0, self.settings.get("sadcaptcha_api_key", ""))

        # 2. Proxy Pool URL
        lbl_pool = tk.Label(container, text="Proxy Pool URL (SOCKS5):", font=("Segoe UI", 10), bg="#0f172a", fg="#f1f5f9")
        lbl_pool.pack(anchor="w")
        self.entry_pool = tk.Entry(container, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", insertbackground="#38bdf8", relief="flat", highlightthickness=1, highlightbackground="#334155")
        self.entry_pool.pack(fill="x", pady=(5, 12), ipady=4)
        self.entry_pool.insert(0, self.settings.get("proxy_pool_url", "https://cu.c69.us/500"))

        # 3. Threads Slider/Entry
        row_thread = tk.Frame(container, bg="#0f172a")
        row_thread.pack(fill="x", pady=(0, 15))

        lbl_threads = tk.Label(row_thread, text="Số luồng chạy song song (Threads):", font=("Segoe UI", 10), bg="#0f172a", fg="#f1f5f9")
        lbl_threads.pack(side="left")
        self.spin_threads = tk.Spinbox(row_thread, from_=1, to=20, width=5, font=("Segoe UI", 10), bg="#1e293b", fg="#f8fafc", buttonbackground="#334155")
        self.spin_threads.pack(side="right")
        self.spin_threads.delete(0, "end")
        self.spin_threads.insert(0, str(self.settings.get("max_threads", 5)))

        # Buttons
        btn_frame = tk.Frame(container, bg="#0f172a")
        btn_frame.pack(fill="x", side="bottom")

        btn_cancel = tk.Button(btn_frame, text="Hủy bỏ", font=("Segoe UI", 10), bg="#334155", fg="#f8fafc", activebackground="#475569", activeforeground="#ffffff", relief="flat", padx=15, pady=6, cursor="hand2", command=self.destroy)
        btn_cancel.pack(side="left")

        btn_save = tk.Button(btn_frame, text="💾 Lưu Cấu Hình", font=("Segoe UI", 10, "bold"), bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff", relief="flat", padx=15, pady=6, cursor="hand2", command=self.save)
        btn_save.pack(side="right")

    def save(self):
        key = self.entry_key.get().strip()
        pool = self.entry_pool.get().strip()
        try:
            threads = int(self.spin_threads.get())
        except ValueError:
            threads = 5

        self.settings["sadcaptcha_api_key"] = key
        self.settings["proxy_pool_url"] = pool
        self.settings["max_threads"] = threads

        if save_settings(self.settings):
            messagebox.showinfo("Thành công", "Đã lưu cấu hình Checker thành công!", parent=self)
            self.destroy()
        else:
            messagebox.showerror("Lỗi", "Không thể lưu tệp cấu hình!", parent=self)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    dlg = CheckerSettingsDialog()
    dlg.mainloop()
