import json
import threading
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import yt_dlp


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

CONFIG_FILE = Path.home() / ".m3u8_downloader.json"


# ---------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------

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
        print(f"Could not save configuration: {e}")


# ---------------------------------------------------------
# FFmpeg setup
# ---------------------------------------------------------

def find_ffmpeg():
    """
    Try to find FFmpeg automatically through PATH.
    """

    import shutil

    ffmpeg = shutil.which("ffmpeg")

    if ffmpeg:
        return ffmpeg

    return None


def ask_for_ffmpeg(root):
    """
    Ask the user to locate ffmpeg.exe.
    """

    messagebox.showinfo(
        "FFmpeg required",
        "FFmpeg is required to download and process HLS videos.\n\n"
        "Please locate your ffmpeg.exe file.",
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
            result = messagebox.askyesno(
                "FFmpeg required",
                "FFmpeg is required.\n\n"
                "Do you want to try selecting it again?",
                parent=root
            )

            if result:
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
    """
    Load saved FFmpeg path, automatically find FFmpeg,
    or ask the user to locate it.
    """

    config = load_config()

    saved_path = config.get("ffmpeg")

    # ---------------------------------------------
    # 1. Check saved path
    # ---------------------------------------------

    if saved_path:

        path = Path(saved_path)

        if path.exists() and path.name.lower() == "ffmpeg.exe":
            return str(path)

    # ---------------------------------------------
    # 2. Check PATH
    # ---------------------------------------------

    ffmpeg = find_ffmpeg()

    if ffmpeg:
        config["ffmpeg"] = ffmpeg
        save_config(config)

        return ffmpeg

    # ---------------------------------------------
    # 3. Ask user
    # ---------------------------------------------

    ffmpeg = ask_for_ffmpeg(root)

    if not ffmpeg:
        return None

    config["ffmpeg"] = ffmpeg
    save_config(config)

    return ffmpeg


# ---------------------------------------------------------
# Main application
# ---------------------------------------------------------

class M3U8Downloader:

    def __init__(self, root, ffmpeg_path):

        self.root = root
        self.ffmpeg_path = ffmpeg_path

        self.root.title("M3U8 Video Downloader")
        self.root.geometry("700x400")
        self.root.resizable(False, False)

        self.url_var = tk.StringVar()
        self.folder_var = tk.StringVar()

        self.status_var = tk.StringVar(
            value="Ready"
        )

        self.progress_var = tk.DoubleVar(
            value=0
        )

        self.create_ui()

    # -----------------------------------------------------
    # UI
    # -----------------------------------------------------

    def create_ui(self):

        main = ttk.Frame(
            self.root,
            padding=25
        )

        main.pack(
            fill="both",
            expand=True
        )

        # ---------------------------------------------
        # Title
        # ---------------------------------------------

        title = ttk.Label(
            main,
            text="M3U8 Video Downloader",
            font=("Segoe UI", 20, "bold")
        )

        title.pack(
            pady=(0, 25)
        )

        # ---------------------------------------------
        # M3U8 URL
        # ---------------------------------------------

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
            pady=(5, 20)
        )

        # ---------------------------------------------
        # Download folder
        # ---------------------------------------------

        ttk.Label(
            main,
            text="Download folder"
        ).pack(
            anchor="w"
        )

        folder_frame = ttk.Frame(main)

        folder_frame.pack(
            fill="x",
            pady=(5, 20)
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

        # ---------------------------------------------
        # Progress bar
        # ---------------------------------------------

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

        # ---------------------------------------------
        # Status
        # ---------------------------------------------

        self.status_label = ttk.Label(
            main,
            textvariable=self.status_var
        )

        self.status_label.pack(
            anchor="w"
        )

        # ---------------------------------------------
        # Download button
        # ---------------------------------------------

        self.download_button = ttk.Button(
            main,
            text="Download",
            command=self.start_download
        )

        self.download_button.pack(
            pady=25
        )

        # ---------------------------------------------
        # FFmpeg status
        # ---------------------------------------------

        ffmpeg_name = Path(
            self.ffmpeg_path
        ).parent

        ttk.Label(
            main,
            text=f"FFmpeg: {self.ffmpeg_path}",
            foreground="gray"
        ).pack(
            anchor="w"
        )

        # Focus URL box
        self.url_entry.focus()

    # -----------------------------------------------------
    # Folder picker
    # -----------------------------------------------------

    def choose_folder(self):

        folder = filedialog.askdirectory(
            parent=self.root,
            title="Choose download folder"
        )

        if folder:
            self.folder_var.set(folder)

    # -----------------------------------------------------
    # Start download
    # -----------------------------------------------------

    def start_download(self):

        url = self.url_var.get().strip()
        folder = self.folder_var.get().strip()

        # ---------------------------------------------
        # Validate URL
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
        # Validate folder
        # ---------------------------------------------

        if not folder:

            messagebox.showwarning(
                "Missing folder",
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
                f"Could not create/access the folder:\n\n{e}",
                parent=self.root
            )

            return

        # ---------------------------------------------
        # Disable controls
        # ---------------------------------------------

        self.download_button.config(
            state="disabled"
        )

        self.browse_button.config(
            state="disabled"
        )

        self.url_entry.config(
            state="disabled"
        )

        self.progress_var.set(0)

        self.status_var.set(
            "Starting download..."
        )

        # ---------------------------------------------
        # Start background thread
        # ---------------------------------------------

        thread = threading.Thread(
            target=self.download,
            args=(url, folder),
            daemon=True
        )

        thread.start()

    # -----------------------------------------------------
    # Download
    # -----------------------------------------------------

    def download(self, url, folder):

        # Create a sensible filename because an m3u8 URL
        # doesn't necessarily contain a useful video title.

        timestamp = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )

        output_template = str(
            Path(folder) / f"video_{timestamp}.%(ext)s"
        )

        options = {

            # Output filename
            "outtmpl": output_template,

            # Best available stream from this playlist
            "format": "best",

            # Tell yt-dlp exactly where FFmpeg is
            "ffmpeg_location": self.ffmpeg_path,

            # We supplied one URL, so don't process a playlist
            "noplaylist": True,

            # Produce MP4 when possible
            "merge_output_format": "mp4",

            # Progress callback
            "progress_hooks": [
                self.progress_hook
            ],

            # Keep console output quiet
            "quiet": True,

            "no_warnings": True,
        }

        try:

            with yt_dlp.YoutubeDL(options) as ydl:

                ydl.download([url])

            self.root.after(
                0,
                self.download_finished
            )

        except Exception as e:

            self.root.after(
                0,
                self.download_failed,
                str(e)
            )

    # -----------------------------------------------------
    # Progress callback
    # -----------------------------------------------------

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
                    "Download finished. Processing video..."
                )
            )

    # -----------------------------------------------------
    # Update progress
    # -----------------------------------------------------

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

        self.status_var.set(
            f"Downloading: {percent_string}  |  "
            f"{speed}  |  ETA: {eta}"
        )

    # -----------------------------------------------------
    # Download complete
    # -----------------------------------------------------

    def download_finished(self):

        self.progress_var.set(100)

        self.status_var.set(
            "Download complete!"
        )

        self.reset_controls()

        another = messagebox.askyesno(
            "Download complete",
            "Video downloaded successfully.\n\n"
            "Do you want to download another video?",
            parent=self.root
        )

        if another:

            # Keep download folder
            self.url_var.set("")

            self.progress_var.set(0)

            self.status_var.set(
                "Ready for another video"
            )

            self.url_entry.focus()

        else:

            self.root.destroy()

    # -----------------------------------------------------
    # Download failed
    # -----------------------------------------------------

    def download_failed(self, error):

        self.reset_controls()

        self.status_var.set(
            "Download failed."
        )

        messagebox.showerror(
            "Download error",
            f"The download failed:\n\n{error}",
            parent=self.root
        )

    # -----------------------------------------------------
    # Restore controls
    # -----------------------------------------------------

    def reset_controls(self):

        self.download_button.config(
            state="normal"
        )

        self.browse_button.config(
            state="normal"
        )

        self.url_entry.config(
            state="normal"
        )


# ---------------------------------------------------------
# Application startup
# ---------------------------------------------------------

def main():

    root = tk.Tk()

    # ---------------------------------------------
    # Find/configure FFmpeg BEFORE main UI
    # ---------------------------------------------

    ffmpeg_path = setup_ffmpeg(root)

    if not ffmpeg_path:

        root.destroy()
        return

    # ---------------------------------------------
    # Start main application
    # ---------------------------------------------

    app = M3U8Downloader(
        root,
        ffmpeg_path
    )

    root.mainloop()


if __name__ == "__main__":
    main()