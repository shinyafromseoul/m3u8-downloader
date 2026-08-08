import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


# =========================================================
# M3U8 Extractor
# =========================================================

class M3U8Extractor:

    def __init__(self, root):

        self.root = root

        self.root.title("M3U8 Extractor")
        self.root.geometry("1000x650")
        self.root.minsize(800, 500)

        self.results = []
        self.browser = None
        self.page = None
        self.playwright = None

        self.url_var = tk.StringVar()
        self.status_var = tk.StringVar(
            value="Enter a webpage URL and click Scan."
        )

        self.create_ui()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close_app
        )

    # =====================================================
    # UI
    # =====================================================

    def create_ui(self):

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
            text="M3U8 Extractor",
            font=("Segoe UI", 20, "bold")
        ).pack(
            pady=(0, 20)
        )

        # -------------------------------------------------
        # URL
        # -------------------------------------------------

        ttk.Label(
            main,
            text="Webpage URL"
        ).pack(
            anchor="w"
        )

        url_frame = ttk.Frame(main)

        url_frame.pack(
            fill="x",
            pady=(5, 10)
        )

        self.url_entry = ttk.Entry(
            url_frame,
            textvariable=self.url_var
        )

        self.url_entry.pack(
            side="left",
            fill="x",
            expand=True
        )

        self.scan_button = ttk.Button(
            url_frame,
            text="Scan",
            command=self.start_scan
        )

        self.scan_button.pack(
            side="left",
            padx=(10, 0)
        )

        # -------------------------------------------------
        # Instructions
        # -------------------------------------------------

        ttk.Label(
            main,
            text=(
                "A browser window will open. Interact with the page normally "
                "and press Play if necessary. Network requests will be "
                "captured automatically."
            ),
            foreground="gray"
        ).pack(
            anchor="w",
            pady=(0, 15)
        )

        # -------------------------------------------------
        # Results
        # -------------------------------------------------

        ttk.Label(
            main,
            text="Detected HLS / M3U8 URLs",
            font=("Segoe UI", 11, "bold")
        ).pack(
            anchor="w"
        )

        result_frame = ttk.Frame(main)

        result_frame.pack(
            fill="both",
            expand=True,
            pady=(5, 10)
        )

        columns = (
            "number",
            "type",
            "url"
        )

        self.tree = ttk.Treeview(
            result_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )

        self.tree.heading(
            "number",
            text="#"
        )

        self.tree.heading(
            "type",
            text="Type"
        )

        self.tree.heading(
            "url",
            text="URL"
        )

        self.tree.column(
            "number",
            width=50,
            anchor="center"
        )

        self.tree.column(
            "type",
            width=100,
            anchor="center"
        )

        self.tree.column(
            "url",
            width=750
        )

        scrollbar = ttk.Scrollbar(
            result_frame,
            orient="vertical",
            command=self.tree.yview
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        # -------------------------------------------------
        # Buttons
        # -------------------------------------------------

        button_frame = ttk.Frame(main)

        button_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Button(
            button_frame,
            text="Copy Selected",
            command=self.copy_selected
        ).pack(
            side="left",
            padx=(0, 5)
        )

        ttk.Button(
            button_frame,
            text="Copy All",
            command=self.copy_all
        ).pack(
            side="left",
            padx=5
        )

        ttk.Button(
            button_frame,
            text="Save List",
            command=self.save_list
        ).pack(
            side="left",
            padx=5
        )

        ttk.Button(
            button_frame,
            text="Clear",
            command=self.clear_results
        ).pack(
            side="right"
        )

        # -------------------------------------------------
        # Status
        # -------------------------------------------------

        ttk.Label(
            main,
            textvariable=self.status_var
        ).pack(
            anchor="w"
        )

        self.url_entry.focus()

    # =====================================================
    # Start scan
    # =====================================================

    def start_scan(self):

        url = self.url_var.get().strip()

        if not url:

            messagebox.showwarning(
                "Missing URL",
                "Please enter a webpage URL.",
                parent=self.root
            )

            return

        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):

            messagebox.showwarning(
                "Invalid URL",
                "Please enter a URL beginning with http:// or https://.",
                parent=self.root
            )

            return

        self.clear_results()

        self.scan_button.config(
            state="disabled"
        )

        self.status_var.set(
            "Starting browser..."
        )

        thread = threading.Thread(
            target=self.scan,
            args=(url,),
            daemon=True
        )

        thread.start()

    # =====================================================
    # Scan page
    # =====================================================

    def scan(self, url):

        try:

            self.playwright = sync_playwright().start()

            self.browser = self.playwright.chromium.launch(
                headless=False
            )

            self.page = self.browser.new_page()

            # -------------------------------------------------
            # Capture requests
            # -------------------------------------------------

            self.page.on(
                "request",
                self.handle_request
            )

            # -------------------------------------------------
            # Capture responses
            # -------------------------------------------------

            self.page.on(
                "response",
                self.handle_response
            )

            self.root.after(
                0,
                lambda: self.status_var.set(
                    "Opening webpage..."
                )
            )

            self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            self.root.after(
                0,
                lambda: self.status_var.set(
                    "Page loaded. Play the video if necessary."
                )
            )

            # -------------------------------------------------
            # Keep browser open
            # -------------------------------------------------

            # Wait until the user closes the browser window.
            #
            # The browser remains interactive, so you can:
            #
            # - click Play
            # - select an episode
            # - navigate around
            #
            # Requests continue being captured.

            while self.browser.is_connected():

                try:

                    if self.page.is_closed():
                        break

                except Exception:
                    break

                self.page.wait_for_timeout(
                    500
                )

        except Exception as e:

            self.root.after(
                0,
                self.scan_error,
                str(e)
            )

        finally:

            self.cleanup_browser()

    # =====================================================
    # Handle request
    # =====================================================

    def handle_request(self, request):

        url = request.url

        # -------------------------------------------------
        # Direct .m3u8 URL
        # -------------------------------------------------

        if ".m3u8" in url.lower():

            self.add_result(
                url,
                "M3U8"
            )

    # =====================================================
    # Handle response
    # =====================================================

    def handle_response(self, response):

        url = response.url

        try:

            content_type = response.headers.get(
                "content-type",
                ""
            ).lower()

        except Exception:

            content_type = ""

        # -------------------------------------------------
        # Detect HLS by content type
        # -------------------------------------------------

        hls_types = (
            "application/vnd.apple.mpegurl",
            "application/x-mpegurl",
            "audio/mpegurl",
            "audio/x-mpegurl"
        )

        is_hls = any(
            content_type.startswith(x)
            for x in hls_types
        )

        if is_hls:

            self.add_result(
                url,
                "HLS"
            )

    # =====================================================
    # Add result
    # =====================================================

    def add_result(self, url, result_type):

        # Ignore duplicates
        if url in self.results:
            return

        self.results.append(
            url
        )

        self.root.after(
            0,
            self.add_result_to_ui,
            url,
            result_type
        )

    # =====================================================
    # Add result to TreeView
    # =====================================================

    def add_result_to_ui(
        self,
        url,
        result_type
    ):

        number = len(
            self.results
        )

        self.tree.insert(
            "",
            "end",
            iid=str(number - 1),
            values=(
                number,
                result_type,
                url
            )
        )

        self.status_var.set(
            f"Found {number} HLS/M3U8 URL(s)."
        )

    # =====================================================
    # Copy selected
    # =====================================================

    def copy_selected(self):

        selected = self.tree.selection()

        if not selected:

            messagebox.showinfo(
                "Nothing selected",
                "Select one or more URLs first.",
                parent=self.root
            )

            return

        urls = []

        for item_id in selected:

            values = self.tree.item(
                item_id,
                "values"
            )

            if values:
                urls.append(
                    values[2]
                )

        self.copy_to_clipboard(
            urls
        )

    # =====================================================
    # Copy all
    # =====================================================

    def copy_all(self):

        if not self.results:

            messagebox.showinfo(
                "No URLs",
                "No M3U8 URLs have been detected yet.",
                parent=self.root
            )

            return

        self.copy_to_clipboard(
            self.results
        )

    # =====================================================
    # Clipboard
    # =====================================================

    def copy_to_clipboard(self, urls):

        text = "\n".join(
            urls
        )

        self.root.clipboard_clear()

        self.root.clipboard_append(
            text
        )

        self.root.update()

        self.status_var.set(
            f"Copied {len(urls)} URL(s) to clipboard."
        )

    # =====================================================
    # Save list
    # =====================================================

    def save_list(self):

        if not self.results:

            messagebox.showinfo(
                "No URLs",
                "There are no URLs to save.",
                parent=self.root
            )

            return

        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save M3U8 URL list",
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )

        if not path:
            return

        try:

            with open(
                path,
                "w",
                encoding="utf-8"
            ) as f:

                for url in self.results:

                    f.write(
                        url + "\n"
                    )

            self.status_var.set(
                f"Saved {len(self.results)} URL(s)."
            )

        except Exception as e:

            messagebox.showerror(
                "Save error",
                str(e),
                parent=self.root
            )

    # =====================================================
    # Clear
    # =====================================================

    def clear_results(self):

        self.results.clear()

        for item in self.tree.get_children():

            self.tree.delete(
                item
            )

        self.status_var.set(
            "Results cleared."
        )

    # =====================================================
    # Scan error
    # =====================================================

    def scan_error(self, error):

        self.scan_button.config(
            state="normal"
        )

        self.status_var.set(
            "Scan failed."
        )

        messagebox.showerror(
            "Extraction error",
            error,
            parent=self.root
        )

    # =====================================================
    # Browser cleanup
    # =====================================================

    def cleanup_browser(self):

        try:

            if self.browser:
                self.browser.close()

        except Exception:
            pass

        try:

            if self.playwright:
                self.playwright.stop()

        except Exception:
            pass

        self.browser = None
        self.page = None
        self.playwright = None

        self.root.after(
            0,
            lambda: self.scan_button.config(
                state="normal"
            )
        )

    # =====================================================
    # Close application
    # =====================================================

    def close_app(self):

        try:

            if self.browser:
                self.browser.close()

        except Exception:
            pass

        try:

            if self.playwright:
                self.playwright.stop()

        except Exception:
            pass

        self.root.destroy()


# =========================================================
# Main
# =========================================================

def main():

    root = tk.Tk()

    app = M3U8Extractor(
        root
    )

    root.mainloop()


if __name__ == "__main__":
    main()