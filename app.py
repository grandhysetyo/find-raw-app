import sys
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import datetime
import re
import json
import time
from pathlib import Path

# Google OAuth
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2 import id_token
from google.auth.transport import requests

RAW_EXTENSIONS = ['.cr2', '.cr3', '.nef', '.arw', '.raf', '.orf', '.rw2']
ALLOWED_EMAILS = ["raysmoments.fg@gmail.com", "raysmoments.grads@gmail.com"]
TOKEN_FILE = "token.json"
TOKEN_EXPIRATION_SECONDS = 7 * 24 * 60 * 60  # 1 minggu
BASE_PATH = getattr(sys, '_MEIPASS', os.path.abspath("."))
CLIENT_SECRET = os.path.join(BASE_PATH, "client_secret.json")


def login_with_google():
    try:
        # Cek token tersimpan
        if Path(TOKEN_FILE).exists():
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                timestamp = data.get("timestamp")
                if timestamp and (time.time() - timestamp) < TOKEN_EXPIRATION_SECONDS:
                    email = data.get("email")
                    return email

        # Login baru via browser
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET,
            scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email']
        )
        credentials = flow.run_local_server(port=0)
        idinfo = id_token.verify_oauth2_token(
            credentials._id_token,
            requests.Request(),
            credentials.client_id
        )
        email = idinfo.get("email")

        # Simpan token lokal
        with open(TOKEN_FILE, "w") as f:
            json.dump({
                "email": email,
                "timestamp": time.time()
            }, f)

        return email

    except Exception as e:
        print("Login gagal:", e)
        return None

class RAWFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RAW File Finder + Google Login")
        self.parent_folder = ""
        self.user_email = None
        self.setup_ui()
        threading.Thread(target=self.try_auto_login).start()

    def setup_ui(self):
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack(fill="both", expand=True)

        login_frame = tk.Frame(frame)
        login_frame.pack(fill="x", pady=(0, 10))
        tk.Button(login_frame, text="🔐 Login dengan Google", command=self.google_login).pack(side="left")
        self.email_label = tk.Label(login_frame, text="Belum login", fg="gray")
        self.email_label.pack(side="left", padx=10)

        tk.Label(frame, text="1. Pilih Folder Parent (berisi folder RAW):").pack(anchor="w")
        folder_frame = tk.Frame(frame)
        folder_frame.pack(fill="x", pady=5)
        self.folder_entry = tk.Entry(folder_frame, width=40)
        self.folder_entry.pack(side="left", fill="x", expand=True)
        tk.Button(folder_frame, text="Browse", command=self.browse_folder).pack(side="right")

        tk.Label(frame, text="2. Masukkan daftar nomor file (satu per baris):").pack(anchor="w", pady=(10, 0))
        self.text_input = tk.Text(frame, height=8)
        self.text_input.pack(fill="both", expand=True, pady=5)

        tk.Label(frame, text="3. Nama Folder Output (opsional):").pack(anchor="w", pady=(10, 0))
        self.output_name_entry = tk.Entry(frame)
        self.output_name_entry.pack(fill="x", pady=(0, 10))

        self.progress_label = tk.Label(frame, text="Progress: 0/0 (0%)", anchor="w")
        self.progress_label.pack(fill="x", pady=(5, 0))
        self.progress = ttk.Progressbar(frame, length=300, mode='determinate')
        self.progress.pack(fill="x", pady=(0, 10))

        self.process_button = tk.Button(frame, text="🔍 Proses", command=self.start_process)
        self.process_button.pack(pady=(0, 10))

        tk.Label(frame, text="Nomor yang tidak ditemukan:", anchor="w").pack(fill="x", pady=(5, 0))
        self.not_found_text = tk.Text(frame, height=6, fg="red")
        self.not_found_text.pack(fill="both", expand=True, pady=(0, 10))

        self.set_input_state(False)

    def set_input_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.folder_entry.config(state=state)
        self.text_input.config(state=state)
        self.output_name_entry.config(state=state)
        self.process_button.config(state=state)
        self.not_found_text.config(state=state)

    def try_auto_login(self):
        email = login_with_google()
        if email:
            self.root.after(0, lambda: self.finish_login(email))

    def google_login(self):
        email = login_with_google()
        if email:
            self.finish_login(email)
        else:
            self.email_label.config(text="Login gagal", fg="red")
            self.user_email = None
            self.set_input_state(False)

    def finish_login(self, email):
        if email not in ALLOWED_EMAILS:
            messagebox.showerror("Akses Ditolak", f"Akun '{email}' tidak diizinkan mengakses aplikasi ini.")
            self.email_label.config(text="Akses ditolak", fg="red")
            self.user_email = None
            self.set_input_state(False)
        else:
            self.email_label.config(text=f"Login sebagai: {email}", fg="green")
            self.user_email = email
            self.set_input_state(True)

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Pilih Folder Parent")
        if folder:
            self.parent_folder = folder
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)

    def start_process(self):
        if not self.user_email:
            messagebox.showerror("Akses Ditolak", "Silakan login dengan akun Google terlebih dahulu.")
            return
        thread = threading.Thread(target=self.process_files)
        thread.start()

    def process_files(self):
        parent = self.folder_entry.get()
        self.not_found_text.delete("1.0", tk.END)

        raw_lines = self.text_input.get("1.0", tk.END).splitlines()
        search_numbers = []

        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            if '.' in line and line.split('.')[0].strip().isdigit():
                parts = line.split('.', 1)
                filename = parts[1].strip()
            else:
                filename = line
            if filename.isdigit():
                search_numbers.append(filename)

        output_name_input = self.output_name_entry.get().strip()
        if output_name_input:
            output_folder_name = output_name_input
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_folder_name = f"RAW_OUTPUT_{timestamp}"

        if not parent or not search_numbers:
            messagebox.showerror("Input Tidak Lengkap", "Harap isi folder parent dan daftar nomor file.")
            return

        raw_folder = os.path.join(parent, "RAW")
        if not os.path.exists(raw_folder):
            messagebox.showerror("Folder RAW Tidak Ditemukan", f"Tidak ada folder 'RAW' dalam {parent}")
            return

        output_folder = os.path.join(parent, output_folder_name)
        os.makedirs(output_folder, exist_ok=True)

        all_raw_files = os.listdir(raw_folder)
        matched = []
        found_numbers = set()

        for file in all_raw_files:
            name, ext = os.path.splitext(file)
            if ext.lower() not in RAW_EXTENSIONS:
                continue
            for number in search_numbers:
                pattern = re.compile(r'(?<!\d)%s$' % re.escape(number))
                if pattern.search(name):
                    matched.append(file)
                    found_numbers.add(number)
                    break

        total = len(matched)
        if total == 0:
            messagebox.showinfo("Tidak Ada File", "Tidak ditemukan file RAW yang cocok.")
            return

        self.progress["value"] = 0
        self.progress["maximum"] = total
        self.update_progress(0, total)

        for i, file in enumerate(matched, 1):
            src = os.path.join(raw_folder, file)
            dst = os.path.join(output_folder, file)
            shutil.copy2(src, dst)
            self.update_progress(i, total)

        messagebox.showinfo("Selesai", f"{total} file berhasil disalin ke:\n{output_folder}")

        not_found_numbers = [num for num in search_numbers if num not in found_numbers]
        if not_found_numbers:
            display_text = "\n".join(not_found_numbers)
            self.not_found_text.insert("1.0", display_text)

    def update_progress(self, current, total):
        percent = int((current / total) * 100)
        self.progress["value"] = current
        self.progress_label.config(text=f"Progress: {current}/{total} ({percent}%)")
        self.root.update_idletasks()

if __name__ == "__main__":
    root = tk.Tk()
    app = RAWFinderApp(root)
    root.geometry("500x750")
    root.mainloop()
