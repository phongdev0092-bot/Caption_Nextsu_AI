import os
import sys
import time
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import core_login

class ModernInsideFPTApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Caption Nextsu AI - Trình Tự Động Đăng Nhập & Quản Lý OTP")
        self.root.geometry("780x780")
        self.root.minsize(700, 700)
        self.root.configure(bg="#0f172a")

        # Load initial config
        self.config = core_login.load_config()

        self.setup_styles()
        self.create_widgets()
        
        # Start TOTP Live Update Loop
        self.update_totp_display()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Colors
        self.bg_color = "#0f172a"
        self.card_bg = "#1e293b"
        self.card_border = "#334155"
        self.text_color = "#f8fafc"
        self.muted_text = "#94a3b8"
        self.accent_blue = "#38bdf8"
        self.accent_green = "#10b981"
        self.accent_orange = "#f59e0b"
        self.accent_red = "#ef4444"

        # Frame styles
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("Card.TFrame", background=self.card_bg)
        
        # Label styles
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=("Segoe UI", 10))
        self.style.configure("Card.TLabel", background=self.card_bg, foreground=self.text_color, font=("Segoe UI", 10))
        self.style.configure("CardMuted.TLabel", background=self.card_bg, foreground=self.muted_text, font=("Segoe UI", 9))
        self.style.configure("Title.TLabel", background=self.bg_color, foreground="#38bdf8", font=("Segoe UI", 16, "bold"))
        self.style.configure("Section.TLabel", background=self.card_bg, foreground="#38bdf8", font=("Segoe UI", 11, "bold"))
        
        # Checkbutton styles
        self.style.configure("TCheckbutton", background=self.card_bg, foreground=self.text_color, font=("Segoe UI", 9))
        self.style.map("TCheckbutton", background=[("active", self.card_bg)])

        # Entry styling
        self.style.configure("TEntry", fieldbackground="#0f172a", foreground="#ffffff", insertcolor="#ffffff")

        # Progress bar
        self.style.configure("Horizontal.TProgressbar", background=self.accent_green, troughcolor="#334155", thickness=6)

    def create_widgets(self):
        # Header
        header_frame = tk.Frame(self.root, bg=self.bg_color)
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        title_lbl = tk.Label(
            header_frame, 
            text="⚡ FPT INSIDE AUTO LOGIN", 
            font=("Segoe UI", 18, "bold"), 
            fg="#38bdf8", 
            bg=self.bg_color
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            header_frame, 
            text="Tự động mở Chrome, tích chọn OTP, điền mật khẩu và xác thực Google Authenticator tức thì", 
            font=("Segoe UI", 9), 
            fg=self.muted_text, 
            bg=self.bg_color
        )
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # Main Scrollable / Stack container
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.pack(fill="both", expand=True, padx=20, pady=5)

        # ----------------- SECTION 1: TOTP LIVE CARD -----------------
        totp_card = tk.Frame(main_container, bg=self.card_bg, highlightbackground=self.card_border, highlightthickness=1)
        totp_card.pack(fill="x", pady=6)

        totp_header = tk.Frame(totp_card, bg=self.card_bg)
        totp_header.pack(fill="x", padx=15, pady=(10, 4))
        
        tk.Label(totp_header, text="🔐 GOOGLE AUTHENTICATOR (OTP)", font=("Segoe UI", 10, "bold"), fg=self.accent_blue, bg=self.card_bg).pack(side="left")
        self.otp_timer_lbl = tk.Label(totp_header, text="Đổi sau 30s", font=("Segoe UI", 9, "bold"), fg=self.accent_orange, bg=self.card_bg)
        self.otp_timer_lbl.pack(side="right")

        # Big OTP Code Display
        otp_body = tk.Frame(totp_card, bg=self.card_bg)
        otp_body.pack(fill="x", padx=15, pady=4)

        self.otp_code_lbl = tk.Label(
            otp_body, 
            text="------", 
            font=("Consolas", 32, "bold"), 
            fg="#22c55e", 
            bg=self.card_bg,
            letter_spacing=4
        )
        self.otp_code_lbl.pack(side="left")

        # Copy OTP Button
        copy_btn = tk.Button(
            otp_body,
            text="📋 Sao chép mã",
            command=self.copy_current_otp,
            bg="#334155",
            fg="#ffffff",
            activebackground="#475569",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2"
        )
        copy_btn.pack(side="right", padx=5)

        # Progress bar for remaining seconds
        self.otp_progress = ttk.Progressbar(totp_card, orient="horizontal", mode="determinate", maximum=30)
        self.otp_progress.pack(fill="x", padx=15, pady=(4, 12))

        # ----------------- SECTION 2: CREDENTIALS CARD -----------------
        cred_card = tk.Frame(main_container, bg=self.card_bg, highlightbackground=self.card_border, highlightthickness=1)
        cred_card.pack(fill="x", pady=6)

        cred_header = tk.Frame(cred_card, bg=self.card_bg)
        cred_header.pack(fill="x", padx=15, pady=(10, 5))
        tk.Label(cred_header, text="👤 THÔNG TIN ĐĂNG NHẬP", font=("Segoe UI", 10, "bold"), fg=self.accent_blue, bg=self.card_bg).pack(side="left")

        form_frame = tk.Frame(cred_card, bg=self.card_bg)
        form_frame.pack(fill="x", padx=15, pady=5)
        form_frame.columnconfigure(1, weight=1)

        # Username
        tk.Label(form_frame, text="Tài khoản:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_bg).grid(row=0, column=0, sticky="w", pady=4)
        self.user_var = tk.StringVar(value=self.config.get("username", "phuongnam.phongnh5"))
        self.user_entry = tk.Entry(form_frame, textvariable=self.user_var, font=("Segoe UI", 10), bg="#0f172a", fg="#ffffff", insertbackground="#ffffff", relief="flat", highlightbackground=self.card_border, highlightthickness=1)
        self.user_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=4, ipady=4)

        # Password
        tk.Label(form_frame, text="Mật khẩu:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_bg).grid(row=1, column=0, sticky="w", pady=4)
        self.pass_var = tk.StringVar(value=self.config.get("password", "Benngo@@2026"))
        self.pass_entry = tk.Entry(form_frame, textvariable=self.pass_var, show="•", font=("Segoe UI", 10), bg="#0f172a", fg="#ffffff", insertbackground="#ffffff", relief="flat", highlightbackground=self.card_border, highlightthickness=1)
        self.pass_entry.grid(row=1, column=1, sticky="ew", padx=(10, 5), pady=4, ipady=4)

        self.show_pass_btn = tk.Button(
            form_frame,
            text="👁",
            command=self.toggle_show_pass,
            bg="#334155",
            fg="#ffffff",
            activebackground="#475569",
            relief="flat",
            cursor="hand2",
            padx=8
        )
        self.show_pass_btn.grid(row=1, column=2, sticky="e", pady=4)

        # Secret Key
        tk.Label(form_frame, text="OTP Secret:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_bg).grid(row=2, column=0, sticky="w", pady=4)
        self.secret_var = tk.StringVar(value=self.config.get("totp_secret", "J5MBXLD2IZJSJWADQU"))
        self.secret_entry = tk.Entry(form_frame, textvariable=self.secret_var, font=("Consolas", 10), bg="#0f172a", fg="#38bdf8", insertbackground="#ffffff", relief="flat", highlightbackground=self.card_border, highlightthickness=1)
        self.secret_entry.grid(row=2, column=1, sticky="ew", padx=(10, 5), pady=4, ipady=4)

        self.qr_import_btn = tk.Button(
            form_frame,
            text="📷 Quét QR",
            command=self.import_qr_image,
            bg="#334155",
            fg="#ffffff",
            activebackground="#475569",
            relief="flat",
            cursor="hand2",
            padx=8,
            font=("Segoe UI", 8)
        )
        self.qr_import_btn.grid(row=2, column=2, sticky="e", pady=4)

        # Options & Save Button
        opts_frame = tk.Frame(cred_card, bg=self.card_bg)
        opts_frame.pack(fill="x", padx=15, pady=(5, 12))

        self.show_browser_var = tk.BooleanVar(value=not self.config.get("headless", False))
        self.keep_open_var = tk.BooleanVar(value=self.config.get("keep_browser_open", True))

        cb1 = tk.Checkbutton(opts_frame, text="Hiển thị trình duyệt Chrome (không chạy ngầm)", variable=self.show_browser_var, bg=self.card_bg, fg=self.text_color, selectcolor="#0f172a", activebackground=self.card_bg, activeforeground=self.text_color, font=("Segoe UI", 9))
        cb1.pack(anchor="w", pady=2)

        cb2 = tk.Checkbutton(opts_frame, text="Giữ Chrome luôn mở sau khi hoàn tất đăng nhập", variable=self.keep_open_var, bg=self.card_bg, fg=self.text_color, selectcolor="#0f172a", activebackground=self.card_bg, activeforeground=self.text_color, font=("Segoe UI", 9))
        cb2.pack(anchor="w", pady=2)

        save_btn = tk.Button(
            opts_frame,
            text="💾 Lưu cấu hình này",
            command=self.save_user_config,
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            relief="flat",
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=3,
            cursor="hand2"
        )
        save_btn.pack(anchor="w", pady=(6, 0))

        # ----------------- SECTION 3: BIG LAUNCH BUTTON -----------------
        launch_frame = tk.Frame(main_container, bg=self.bg_color)
        launch_frame.pack(fill="x", pady=10)

        self.btn_launch = tk.Button(
            launch_frame,
            text="🚀 BẮT ĐẦU ĐĂNG NHẬP INSIDE.FPT.NET NGAY",
            command=self.start_login_process,
            bg="#16a34a",
            fg="#ffffff",
            activebackground="#15803d",
            activeforeground="#ffffff",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            pady=12,
            cursor="hand2"
        )
        self.btn_launch.pack(fill="x")

        # ----------------- SECTION 4: ACTIVITY LOG -----------------
        log_card = tk.Frame(main_container, bg=self.card_bg, highlightbackground=self.card_border, highlightthickness=1)
        log_card.pack(fill="both", expand=True, pady=6)

        log_header = tk.Frame(log_card, bg=self.card_bg)
        log_header.pack(fill="x", padx=15, pady=(8, 4))
        tk.Label(log_header, text="📝 NHẬT KÝ THỰC THI (LOGS)", font=("Segoe UI", 9, "bold"), fg=self.muted_text, bg=self.card_bg).pack(side="left")

        # Scrolled Text
        self.log_text = tk.Text(
            log_card,
            bg="#0b1120",
            fg="#e2e8f0",
            insertbackground="#ffffff",
            font=("Consolas", 9),
            relief="flat",
            highlightthickness=0,
            wrap="word",
            height=8
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Configure tag colors for logs
        self.log_text.tag_configure("info", foreground="#38bdf8")
        self.log_text.tag_configure("success", foreground="#4ade80")
        self.log_text.tag_configure("warning", foreground="#fbbf24")
        self.log_text.tag_configure("error", foreground="#f87171")
        self.log_text.tag_configure("timestamp", foreground="#64748b")

        self.append_log("Hệ thống đã sẵn sàng. Bấm nút màu xanh phía trên để đăng nhập tự động.", "info")

    def toggle_show_pass(self):
        if self.pass_entry.cget("show") == "":
            self.pass_entry.configure(show="•")
            self.show_pass_btn.configure(text="👁")
        else:
            self.pass_entry.configure(show="")
            self.show_pass_btn.configure(text="🙈")

    def copy_current_otp(self):
        code = self.otp_code_lbl.cget("text")
        if code and code != "------":
            self.root.clipboard_clear()
            self.root.clipboard_append(code)
            self.append_log(f"Đã sao chép mã OTP [{code}] vào bộ nhớ tạm (Clipboard)!", "success")

    def import_qr_image(self):
        file_path = filedialog.askopenfilename(
            title="Chọn hình ảnh mã QR Google Authenticator",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"), ("All files", "*.*")]
        )
        if file_path:
            try:
                sec, name = core_login.extract_secret_from_qr_image(file_path)
                self.secret_var.set(sec)
                self.save_user_config()
                self.append_log(f"Đã quét thành công mã QR! Tài khoản: {name}, Secret: {sec}", "success")
                messagebox.showinfo("Thành công", f"Đã nhận diện thành công mã QR!\nKhóa bí mật: {sec}")
            except Exception as e:
                self.append_log(f"Lỗi khi đọc mã QR: {e}", "error")
                messagebox.showerror("Lỗi đọc QR", str(e))

    def update_totp_display(self):
        try:
            secret = self.secret_var.get().strip()
            if secret:
                code, rem = core_login.get_totp_info(secret)
                self.otp_code_lbl.configure(text=code)
                self.otp_timer_lbl.configure(text=f"Đổi sau: {rem}s")
                self.otp_progress["value"] = rem
            else:
                self.otp_code_lbl.configure(text="------")
                self.otp_timer_lbl.configure(text="Chưa có Secret")
        except Exception:
            self.otp_code_lbl.configure(text="ERR")
        
        # Poll every 1 second
        self.root.after(1000, self.update_totp_display)

    def save_user_config(self):
        self.config["username"] = self.user_var.get().strip()
        self.config["password"] = self.pass_var.get().strip()
        self.config["totp_secret"] = self.secret_var.get().strip()
        self.config["headless"] = not self.show_browser_var.get()
        self.config["keep_browser_open"] = self.keep_open_var.get()
        core_login.save_config(self.config)
        self.append_log("Đã lưu cấu hình tài khoản vào config.json thành công.", "success")

    def append_log(self, message, status="info"):
        def _write():
            now_str = time.strftime("[%H:%M:%S] ")
            self.log_text.insert("end", now_str, "timestamp")
            self.log_text.insert("end", f"[{status.upper()}] ", status)
            self.log_text.insert("end", f"{message}\n")
            self.log_text.see("end")
        self.root.after(0, _write)

    def start_login_process(self):
        # Disable button while executing
        self.btn_launch.configure(state="disabled", text="⏳ ĐANG THỰC HIỆN ĐĂNG NHẬP...", bg="#475569")
        
        # Save config first
        self.save_user_config()

        def worker():
            try:
                username = self.user_var.get().strip()
                password = self.pass_var.get().strip()
                secret = self.secret_var.get().strip()
                headless = not self.show_browser_var.get()
                keep_open = self.keep_open_var.get()

                core_login.run_fpt_login(
                    username=username,
                    password=password,
                    secret=secret,
                    headless=headless,
                    keep_open=keep_open,
                    log_callback=self.append_log
                )
                self.append_log("===> QUÁ TRÌNH ĐĂNG NHẬP HOÀN TẤT THÀNH CÔNG! <===", "success")
            except Exception as e:
                self.append_log(f"===> ĐĂNG NHẬP KHÔNG THÀNH CÔNG: {e} <===", "error")
            finally:
                self.root.after(0, lambda: self.btn_launch.configure(
                    state="normal", 
                    text="🚀 BẮT ĐẦU ĐĂNG NHẬP INSIDE.FPT.NET NGAY", 
                    bg="#16a34a"
                ))

        threading.Thread(target=worker, daemon=True).start()

def main():
    root = tk.Tk()
    app = ModernInsideFPTApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
