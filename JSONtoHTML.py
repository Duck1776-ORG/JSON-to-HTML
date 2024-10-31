import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import requests
import os
import json
from json2html import json2html
import threading
import queue

class JsonDownloaderConverter:
    def __init__(self, master):
        self.master = master
        master.title("JSON Downloader and Converter")
        master.geometry("600x400")

        self.url_label = tk.Label(master, text="Enter webpage URL:")
        self.url_label.pack(pady=(10, 0))
        self.url_entry = tk.Entry(master, width=60)
        self.url_entry.pack()

        self.output_label = tk.Label(master, text="Output directory:")
        self.output_label.pack(pady=(10, 0))
        self.output_frame = tk.Frame(master)
        self.output_frame.pack(fill=tk.X, padx=10)
        self.output_entry = tk.Entry(self.output_frame, width=50)
        self.output_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.output_button = tk.Button(self.output_frame, text="Browse...", command=self.browse_output)
        self.output_button.pack(side=tk.RIGHT)

        self.button_frame = tk.Frame(master)
        self.button_frame.pack(pady=10)
        self.download_button = tk.Button(self.button_frame, text="Download JSON", command=self.start_download)
        self.download_button.pack(side=tk.LEFT, padx=5)
        self.convert_button = tk.Button(self.button_frame, text="Convert to HTML", command=self.start_conversion, state=tk.DISABLED)
        self.convert_button.pack(side=tk.LEFT, padx=5)

        self.progress_label = tk.Label(master, text="Progress:")
        self.progress_label.pack(pady=(10, 0))
        self.progress_bar = ttk.Progressbar(master, orient='horizontal', length=500, mode='determinate')
        self.progress_bar.pack(pady=(5, 10))

        self.status_label = tk.Label(master, text="")
        self.status_label.pack(pady=5)

        self.json_files = []

    def browse_output(self):
        directory = filedialog.askdirectory()
        self.output_entry.delete(0, tk.END)
        self.output_entry.insert(0, directory)

    def start_download(self):
        url = self.url_entry.get()
        output_dir = self.output_entry.get()

        if not url or not output_dir:
            messagebox.showwarning('Input Error', 'Please provide both URL and output directory.')
            return

        self.download_button.config(state=tk.DISABLED)
        self.convert_button.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self.status_label.config(text="Downloading...")

        threading.Thread(target=self.download_json, args=(url, output_dir), daemon=True).start()

    def download_json(self, url, output_dir):
        try:
            response = requests.get(url)
            response.raise_for_status()
            links = response.text.split('"')
            json_links = [link for link in links if link.lower().endswith('.json')]

            json_dir = os.path.join(output_dir, 'json files')
            os.makedirs(json_dir, exist_ok=True)

            total_files = len(json_links)
            for i, link in enumerate(json_links, 1):
                if not link.startswith('http'):
                    link = f"{url.rstrip('/')}/{link.lstrip('/')}"
                
                file_name = os.path.basename(link)
                file_path = os.path.join(json_dir, file_name)

                json_response = requests.get(link)
                json_response.raise_for_status()

                with open(file_path, 'wb') as file:
                    file.write(json_response.content)

                self.json_files.append(file_path)
                self.update_progress(i / total_files * 100)

            self.master.after(0, self.download_complete)
        except Exception as e:
            self.master.after(0, lambda: self.show_error(f"Error during download: {str(e)}"))

    def download_complete(self):
        self.status_label.config(text="Download completed.")
        self.convert_button.config(state=tk.NORMAL)
        self.download_button.config(state=tk.NORMAL)

    def start_conversion(self):
        output_dir = self.output_entry.get()
        html_dir = os.path.join(output_dir, 'html files')
        os.makedirs(html_dir, exist_ok=True)

        self.convert_button.config(state=tk.DISABLED)
        self.download_button.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self.status_label.config(text="Converting...")

        threading.Thread(target=self.convert_json_to_html, args=(html_dir,), daemon=True).start()

    def convert_json_to_html(self, html_dir):
        try:
            total_files = len(self.json_files)
            for i, json_file in enumerate(self.json_files, 1):
                with open(json_file, 'r') as file:
                    json_data = json.load(file)

                html_content = json2html.convert(json=json_data)
                html_filename = os.path.basename(json_file).replace('.json', '.html')
                html_path = os.path.join(html_dir, html_filename)

                with open(html_path, 'w', encoding='utf-8') as file:
                    file.write(html_content)

                self.update_progress(i / total_files * 100)

            self.master.after(0, self.conversion_complete)
        except Exception as e:
            self.master.after(0, lambda: self.show_error(f"Error during conversion: {str(e)}"))

    def conversion_complete(self):
        self.status_label.config(text="Conversion completed.")
        self.convert_button.config(state=tk.NORMAL)
        self.download_button.config(state=tk.NORMAL)

    def update_progress(self, value):
        self.master.after(0, lambda: self.progress_bar.config(value=value))

    def show_error(self, message):
        messagebox.showerror("Error", message)
        self.download_button.config(state=tk.NORMAL)
        self.convert_button.config(state=tk.NORMAL)

if __name__ == '__main__':
    root = tk.Tk()
    app = JsonDownloaderConverter(root)
    root.mainloop()