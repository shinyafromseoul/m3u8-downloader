import json
import shutil
import threading
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import yt_dlp


# =========================================================
# Configuration
# =========================================================

CONFIG_FILE = Path.home() / ".m3u8_downloader.json"


def load_config():
    if not CONFIG_FILE.exists():
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Could not save config: {e}")


# =========================================================
# FFmpeg
# =========================================================

def find_ffmpeg():
    return shutil.which("ffmpeg")


def ask_for_ffmpeg(root):

    messagebox.showinfo(
        "FFmpeg required",
        "FFmpeg is required for downloading HLS videos.\n\n"
        "Please locate ffmpeg.exe.",
        parent=root
    )

    while True:

        path = filedialog.askopenfilename(
            parent=root,
            title="Locate ffmpeg.exe",
            filetypes=[
                ("FFmpeg executable", "ffmpeg.exe"),
                ("Executable files", "*.exe"),
                ("All files", "*.*")
            ]
        )

        if not path:
            retry = messagebox.askyesno(
                "FFmpeg required",
                "FFmpeg is required.\n\n"
                "Do you want to try again?",
                parent=root
            )

            if retry:
                continue

            return None

        selected = Path(path)

        if selected.name.lower() != "ffmpeg.exe":

            messagebox.showwarning(
                "Invalid file",
                "Please select ffmpeg.exe.",
                parent=root
            )

            continue

        if not selected.exists():

            messagebox.showerror(
                "File not found",
                "The selected file does not exist.",
                parent=root
            )

            continue

        return str(selected)


def setup_ffmpeg(root):

    config = load_config()

    # Saved path
    saved = config.get("ffmpeg")

    if saved:

        path = Path(saved)

        if path.exists() and path.name.lower() == "ffmpeg.exe":
            return str(path)

    # PATH
    ffmpeg = find_ffmpeg()

    if ffmpeg:

        config["ffmpeg"] = ffmpeg
        save_config(config)

        return ffmpeg

    # Ask user
    ffmpeg = ask_for_ffmpeg(root)

    if not ffmpeg:
        return None

    config["ffmpeg"] = ffmpeg
    save_config(config)

    return ffmpeg


# =========================================================
# Main application
# =========================================================

class M3U8Downloader:

    def __init__(self, root, ffmpeg_path):

        self.root = root
        self.ffmpeg_path = ffmpeg_path

        self.queue = []

        self.downloading = False
        self.stop_requested = False

        self.current_index = None

        self.url_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.folder_var = tk.StringVar()

        self.status_var = tk.StringVar(
            value="Ready"
        )

        self.progress_var = tk.DoubleVar(
            value=0
        )

        self.load_saved_data()

        self.create_ui()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        self.refresh_queue()

    # =====================================================
    # Saved data
    # =====================================================

    def load_saved_data(self):

        config = load_config()

        # Restore download folder
        self.folder_var.set(
            config.get("download_folder", "")
        )

        # Restore queue
        saved_queue = config.get("queue", [])

        if isinstance(saved_queue, list):
            self.queue = saved_queue

    def save_data(self):

        config = load_config()

        config["ffmpeg"] = self.ffmpeg_path

        config["download_folder"] = (
            self.folder_var.get()
        )

        config["queue"] = self.queue

        save_config(config)

    # =====================================================
    # UI
    # =====================================================

    def create_ui(self):

        self.root.title(
            "M3U8 Video Downloader"
        )

        self.root.geometry(
            "850x650"
        )

        self.root.minsize(
            750,
            550
        )

        main = ttk.Frame(
            self.root,
            padding=20
        )

        main.pack(
            fill="both",
            expand=True
        )

        # -------------------------------------------------
        # Title
        # -------------------------------------------------

        ttk.Label(
            main,
            text="M3U8 Video Downloader",
            font=("Segoe UI", 20, "bold")
        ).pack(
            pady=(0, 20)
        )

        # -------------------------------------------------
        # URL
        # -------------------------------------------------

        ttk.Label(
            main,
            text="M3U8 URL"
        ).pack(
            anchor="w"
        )

        self.url_entry = ttk.Entry(
            main,
            textvariable=self.url_var
        )

        self.url_entry.pack(
            fill="x",
            pady=(5, 10)
        )

        # -------------------------------------------------
        # Name
        # -------------------------------------------------

        ttk.Label(
            main,
            text="Video name"
        ).pack(
            anchor="w"
        )

        name_frame = ttk.Frame(main)

        name_frame.pack(
            fill="x",
            pady=(5, 10)
        )

        self.name_entry = ttk.Entry(
            name_frame,
            textvariable=self.name_var
        )

        self.name_entry.pack(
            side="left",
            fill="x",
            expand=True
        )

        ttk.Label(
            name_frame,
            text=".mp4"
        ).pack(
            side="right",
            padx=(8, 0)
        )

        # -------------------------------------------------
        # Add button
        # -------------------------------------------------

        self.add_button = ttk.Button(
            main,
            text="Add to Queue",
            command=self.add_to_queue
        )

        self.add_button.pack(
            pady=(5, 15)
        )

        # -------------------------------------------------
        # Queue label
        # -------------------------------------------------

        ttk.Label(
            main,
            text="Download Queue",
            font=("Segoe UI", 11, "bold")
        ).pack(
            anchor="w"
        )

        # -------------------------------------------------
        # Queue table
        # -------------------------------------------------

        queue_frame = ttk.Frame(main)

        queue_frame.pack(
            fill="both",
            expand=True,
            pady=(5, 10)
        )

        columns = (
            "number",
            "name",
            "status"
        )

        self.queue_tree = ttk.Treeview(
            queue_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )

        self.queue_tree.heading(
            "number",
            text="#"
        )

        self.queue_tree.heading(
            "name",
            text="Video"
        )

        self.queue_tree.heading(
            "status",
            text="Status"
        )

        self.queue_tree.column(
            "number",
            width=45,
            anchor="center"
        )

        self.queue_tree.column(
            "name",
            width=500
        )

        self.queue_tree.column(
            "status",
            width=130,
            anchor="center"
        )

        scrollbar = ttk.Scrollbar(
            queue_frame,
            orient="vertical",
            command=self.queue_tree.yview
        )

        self.queue_tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.queue_tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        # -------------------------------------------------
        # Queue controls
        # -------------------------------------------------

        queue_buttons = ttk.Frame(main)

        queue_buttons.pack(
            fill="x",
            pady=(0, 15)
        )

        ttk.Button(
            queue_buttons,
            text="↑ Move Up",
            command=self.move_up
        ).pack(
            side="left",
            padx=(0, 5)
        )

        ttk.Button(
            queue_buttons,
            text="↓ Move Down",
            command=self.move_down
        ).pack(
            side="left",
            padx=5
        )

        ttk.Button(
            queue_buttons,
            text="Remove Selected",
            command=self.remove_selected
        ).pack(
            side="left",
            padx=5
        )

        ttk.Button(
            queue_buttons,
            text="Retry Failed",
            command=self.retry_failed
        ).pack(
            side="left",
            padx=5
        )

        ttk.Button(
            queue_buttons,
            text="Clear Completed",
            command=self.clear_completed
        ).pack(
            side="right"
        )

        # -------------------------------------------------
        # Download folder
        # -------------------------------------------------

        ttk.Label(
            main,
            text="Download folder"
        ).pack(
            anchor="w"
        )

        folder_frame = ttk.Frame(main)

        folder_frame.pack(
            fill="x",
            pady=(5, 10)
        )

        self.folder_entry = ttk.Entry(
            folder_frame,
            textvariable=self.folder_var
        )

        self.folder_entry.pack(
            side="left",
            fill="x",
            expand=True
        )

        self.browse_button = ttk.Button(
            folder_frame,
            text="Browse...",
            command=self.choose_folder
        )

        self.browse_button.pack(
            side="right",
            padx=(10, 0)
        )

        # -------------------------------------------------
        # Progress
        # -------------------------------------------------

        self.progress = ttk.Progressbar(
            main,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            variable=self.progress_var
        )

        self.progress.pack(
            fill="x",
            pady=(10, 5)
        )

        self.status_label = ttk.Label(
            main,
            textvariable=self.status_var
        )

        self.status_label.pack(
            anchor="w"
        )

        # -------------------------------------------------
        # Start button
        # -------------------------------------------------

        self.start_button = ttk.Button(
            main,
            text="Download Queue",
            command=self.start_queue
        )

        self.start_button.pack(
            pady=15
        )

        # -------------------------------------------------
        # FFmpeg info
        # -------------------------------------------------

        ttk.Label(
            main,
            text=f"FFmpeg: {self.ffmpeg_path}",
            foreground="gray"
        ).pack(
            anchor="w"
        )

    # =====================================================
    # Add queue item
    # =====================================================

    def add_to_queue(self):

        url = self.url_var.get().strip()

        name = self.name_var.get().strip()

        # ---------------------------------------------
        # URL validation
        # ---------------------------------------------

        if not url:

            messagebox.showwarning(
                "Missing URL",
                "Please enter an m3u8 URL.",
                parent=self.root
            )

            return

        if ".m3u8" not in url.lower():

            messagebox.showwarning(
                "Invalid URL",
                "The URL does not appear to be an m3u8 playlist.",
                parent=self.root
            )

            return

        # ---------------------------------------------
        # Name
        # ---------------------------------------------

        if not name:

            name = f"video_{len(self.queue) + 1}"

        # Remove extension if user entered it
        if name.lower().endswith(".mp4"):
            name = name[:-4]

        # ---------------------------------------------
        # Create queue item
        # ---------------------------------------------

        item = {
            "url": url,
            "name": name,
            "status": "Waiting"
        }

        self.queue.append(item)

        self.save_data()

        self.refresh_queue()

        # Clear URL/name
        self.url_var.set("")
        self.name_var.set("")

        self.url_entry.focus()

    # =====================================================
    # Refresh queue display
    # =====================================================

    def refresh_queue(self):

        for item in self.queue_tree.get_children():

            self.queue_tree.delete(item)

        for index, item in enumerate(self.queue):

            self.queue_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    index + 1,
                    item.get("name", "Unknown"),
                    item.get("status", "Waiting")
                )
            )

    # =====================================================
    # Remove selected
    # =====================================================

    def remove_selected(self):

        if self.downloading:

            messagebox.showinfo(
                "Download in progress",
                "You cannot modify the queue while downloading.",
                parent=self.root
            )

            return

        selected = self.queue_tree.selection()

        if not selected:
            return

        indexes = sorted(
            [int(x) for x in selected],
            reverse=True
        )

        for index in indexes:

            if 0 <= index < len(self.queue):
                self.queue.pop(index)

        self.save_data()
        self.refresh_queue()

    # =====================================================
    # Move up
    # =====================================================

    def move_up(self):

        if self.downloading:
            return

        selected = self.queue_tree.selection()

        if len(selected) != 1:
            return

        index = int(selected[0])

        if index <= 0:
            return

        self.queue[index], self.queue[index - 1] = (
            self.queue[index - 1],
            self.queue[index]
        )

        self.save_data()
        self.refresh_queue()

        self.queue_tree.selection_set(
            str(index - 1)
        )

    # =====================================================
    # Move down
    # =====================================================

    def move_down(self):

        if self.downloading:
            return

        selected = self.queue_tree.selection()

        if len(selected) != 1:
            return

        index = int(selected[0])

        if index >= len(self.queue) - 1:
            return

        self.queue[index], self.queue[index + 1] = (
            self.queue[index + 1],
            self.queue[index]
        )

        self.save_data()
        self.refresh_queue()

        self.queue_tree.selection_set(
            str(index + 1)
        )

    # =====================================================
    # Retry failed
    # =====================================================

    def retry_failed(self):

        if self.downloading:
            return

        changed = False

        for item in self.queue:

            if item.get("status") == "Failed":

                item["status"] = "Waiting"

                changed = True

        if changed:

            self.save_data()
            self.refresh_queue()

    # =====================================================
    # Clear completed
    # =====================================================

    def clear_completed(self):

        if self.downloading:
            return

        self.queue = [
            item
            for item in self.queue
            if item.get("status") != "Complete"
        ]

        self.save_data()
        self.refresh_queue()

    # =====================================================
    # Folder
    # =====================================================

    def choose_folder(self):

        folder = filedialog.askdirectory(
            parent=self.root,
            title="Choose download folder"
        )

        if folder:

            self.folder_var.set(folder)

            self.save_data()

    # =====================================================
    # Start queue
    # =====================================================

    def start_queue(self):

        if self.downloading:
            return

        if not self.queue:

            messagebox.showinfo(
                "Queue empty",
                "Add some videos to the queue first.",
                parent=self.root
            )

            return

        folder = self.folder_var.get().strip()

        if not folder:

            messagebox.showwarning(
                "Download folder",
                "Please choose a download folder.",
                parent=self.root
            )

            return

        try:

            Path(folder).mkdir(
                parents=True,
                exist_ok=True
            )

        except Exception as e:

            messagebox.showerror(
                "Folder error",
                f"Could not access the folder:\n\n{e}",
                parent=self.root
            )

            return

        # Only start if there are waiting items
        waiting = any(
            item.get("status") == "Waiting"
            for item in self.queue
        )

        if not waiting:

            messagebox.showinfo(
                "Nothing to download",
                "There are no waiting videos in the queue.",
                parent=self.root
            )

            return

        self.downloading = True

        self.start_button.config(
            state="disabled"
        )

        self.add_button.config(
            state="disabled"
        )

        self.browse_button.config(
            state="disabled"
        )

        self.save_data()

        thread = threading.Thread(
            target=self.process_queue,
            daemon=True
        )

        thread.start()

    # =====================================================
    # Process queue
    # =====================================================

    def process_queue(self):

        while True:

            next_index = None

            # Find next waiting item
            for index, item in enumerate(self.queue):

                if item.get("status") == "Waiting":

                    next_index = index
                    break

            if next_index is None:
                break

            self.current_index = next_index

            item = self.queue[next_index]

            item["status"] = "Downloading"

            self.save_data()

            self.root.after(
                0,
                self.refresh_queue
            )

            self.root.after(
                0,
                self.update_current_status,
                item["name"]
            )

            success, error = self.download_item(
                item
            )

            if success:

                item["status"] = "Complete"

            else:

                item["status"] = "Failed"

                print(
                    f"Download failed: {item['name']}"
                )

                print(error)

            self.save_data()

            self.root.after(
                0,
                self.refresh_queue
            )

        self.root.after(
            0,
            self.queue_finished
        )

    # =====================================================
    # Download individual item
    # =====================================================

    def download_item(self, item):

        folder = Path(
            self.folder_var.get()
        )

        name = self.clean_filename(
            item["name"]
        )

        output_template = str(
            folder / f"{name}.%(ext)s"
        )

        options = {

            "outtmpl": output_template,

            "format": "best",

            "ffmpeg_location": self.ffmpeg_path,

            "noplaylist": True,

            "merge_output_format": "mp4",

            "progress_hooks": [
                self.progress_hook
            ],

            "quiet": True,

            "no_warnings": True,
        }

        try:

            with yt_dlp.YoutubeDL(options) as ydl:

                ydl.download([
                    item["url"]
                ])

            return True, None

        except Exception as e:

            return False, str(e)

    # =====================================================
    # Filename cleanup
    # =====================================================

    @staticmethod
    def clean_filename(name):

        invalid_chars = '<>:"/\\|?*'

        for char in invalid_chars:

            name = name.replace(
                char,
                "_"
            )

        name = name.strip()

        if not name:
            name = "video"

        return name

    # =====================================================
    # Progress callback
    # =====================================================

    def progress_hook(self, data):

        if data["status"] == "downloading":

            percent_string = data.get(
                "_percent_str",
                "0%"
            )

            speed = data.get(
                "_speed_str",
                "?"
            )

            eta = data.get(
                "_eta_str",
                "?"
            )

            try:

                percent = float(
                    percent_string
                    .replace("%", "")
                    .strip()
                )

            except ValueError:

                percent = 0

            self.root.after(
                0,
                self.update_progress,
                percent,
                percent_string,
                speed,
                eta
            )

        elif data["status"] == "finished":

            self.root.after(
                0,
                lambda: self.status_var.set(
                    "Downloading finished. Processing video..."
                )
            )

    # =====================================================
    # Progress UI
    # =====================================================

    def update_progress(
        self,
        percent,
        percent_string,
        speed,
        eta
    ):

        self.progress_var.set(
            percent
        )

        if self.current_index is not None:

            name = self.queue[
                self.current_index
            ]["name"]

        else:

            name = "Video"

        self.status_var.set(
            f"{name}  |  "
            f"{percent_string}  |  "
            f"{speed}  |  "
            f"ETA {eta}"
        )

    # =====================================================
    # Current video
    # =====================================================

    def update_current_status(self, name):

        self.progress_var.set(0)

        self.status_var.set(
            f"Starting: {name}"
        )

    # =====================================================
    # Queue finished
    # =====================================================

    def queue_finished(self):

        self.downloading = False

        self.current_index = None

        self.start_button.config(
            state="normal"
        )

        self.add_button.config(
            state="normal"
        )

        self.browse_button.config(
            state="normal"
        )

        self.progress_var.set(0)

        self.refresh_queue()

        completed = sum(
            item.get("status") == "Complete"
            for item in self.queue
        )

        failed = sum(
            item.get("status") == "Failed"
            for item in self.queue
        )

        self.status_var.set(
            f"Queue finished  |  "
            f"Completed: {completed}  |  "
            f"Failed: {failed}"
        )

        if failed:

            messagebox.showwarning(
                "Queue finished",
                f"Queue finished.\n\n"
                f"Completed: {completed}\n"
                f"Failed: {failed}\n\n"
                f"You can click 'Retry Failed' to try them again.",
                parent=self.root
            )

        else:

            messagebox.showinfo(
                "Queue finished",
                f"All videos downloaded successfully!\n\n"
                f"Completed: {completed}",
                parent=self.root
            )

    # =====================================================
    # Close
    # =====================================================

    def on_close(self):

        if self.downloading:

            answer = messagebox.askyesno(
                "Download in progress",
                "A download is currently running.\n\n"
                "If you close the app, the current download "
                "will be interrupted.\n\n"
                "Close anyway?",
                parent=self.root
            )

            if not answer:
                return

        self.save_data()

        self.root.destroy()


# =========================================================
# Start
# =========================================================

def main():

    root = tk.Tk()

    ffmpeg_path = setup_ffmpeg(root)

    if not ffmpeg_path:

        root.destroy()
        return

    app = M3U8Downloader(
        root,
        ffmpeg_path
    )

    root.mainloop()


if __name__ == "__main__":
    main()