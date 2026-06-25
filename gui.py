import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
from crawler import SimpleCrawler


class CrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Web Crawler GUI")
        self.root.geometry("800x600")
        self.crawler = None
        self.crawling = False

        # URL Input
        tk.Label(root, text="Start URL:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.url_entry = tk.Entry(root, width=60)
        self.url_entry.insert(0, "https://example.com")
        self.url_entry.grid(row=0, column=1, padx=10, pady=5)

        # Parameters Frame
        params_frame = ttk.LabelFrame(root, text="Parameters", padding=10)
        params_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        tk.Label(params_frame, text="Max Pages:").grid(row=0, column=0, sticky="w")
        self.max_pages_var = tk.StringVar(value="10")
        self.max_pages = tk.Spinbox(params_frame, from_=1, to=1000, width=10, textvariable=self.max_pages_var)
        self.max_pages.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(params_frame, text="Max Depth:").grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.max_depth_var = tk.StringVar(value="2")
        self.max_depth = tk.Spinbox(params_frame, from_=1, to=10, width=10, textvariable=self.max_depth_var)
        self.max_depth.grid(row=0, column=3, sticky="w", padx=5)

        tk.Label(params_frame, text="Delay (sec):").grid(row=0, column=4, sticky="w", padx=(20, 0))
        self.delay_var = tk.StringVar(value="0.5")
        self.delay = tk.Spinbox(params_frame, from_=0.1, to=5.0, width=10, increment=0.1, textvariable=self.delay_var)
        self.delay.grid(row=0, column=5, sticky="w", padx=5)

        tk.Label(params_frame, text="Same Domain:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.same_domain = tk.BooleanVar(value=True)
        tk.Checkbutton(params_frame, variable=self.same_domain).grid(row=1, column=1, sticky="w", pady=(10, 0))

        # Buttons
        button_frame = tk.Frame(root)
        button_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        self.start_btn = tk.Button(button_frame, text="Start Crawl", command=self.start_crawl, bg="#4CAF50", fg="white", padx=15, pady=5)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(button_frame, text="Stop", command=self.stop_crawl, bg="#f44336", fg="white", padx=15, pady=5, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = tk.Button(button_frame, text="Clear Results", command=self.clear_results, padx=15, pady=5)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # Output
        tk.Label(root, text="Results:").grid(row=3, column=0, sticky="w", padx=10, pady=(10, 0))
        self.output = scrolledtext.ScrolledText(root, height=20, width=100, wrap=tk.WORD)
        self.output.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=5, column=0, columnspan=2, sticky="ew")

        root.columnconfigure(1, weight=1)
        root.rowconfigure(4, weight=1)

    def start_crawl(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return

        self.crawling = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.output.delete(1.0, tk.END)
        self.status_var.set("Crawling...")

        # Run in thread to not block GUI
        thread = threading.Thread(target=self._crawl_worker, args=(url,), daemon=True)
        thread.start()

    def _crawl_worker(self, url):
        try:
            self.crawler = SimpleCrawler(
                url,
                max_pages=int(self.max_pages_var.get()),
                max_depth=int(self.max_depth_var.get()),
                delay=float(self.delay_var.get()),
                same_domain=self.same_domain.get(),
                verify_ssl=False
            )

            results = self.crawler.crawl()

            self.output.insert(tk.END, f"✓ Crawl completed!\n\n")
            self.output.insert(tk.END, f"Total pages crawled: {len(results)}\n\n")
            self.output.insert(tk.END, "=" * 150 + "\n")
            self.output.insert(tk.END, f"{'URL':<60} | {'Title':<30} | {'Tags':<20} | {'Year':<6} | {'Transcript':<20}\n")
            self.output.insert(tk.END, "=" * 150 + "\n")

            for item in results:
                item_url = item.get("url", "")[:60]
                item_title = item.get("title", "")[:30]
                
                tags = ", ".join(item.get("tags", [])[:3]) if "tags" in item else "-"
                tags = tags[:20]
                
                year = str(item.get("year", "-"))[:6]
                
                transcript_status = item.get("transcript_available", "No transcript available")
                if "youtube_captions" in item and item["youtube_captions"]:
                    captions = item["youtube_captions"]
                    has_transcript = any("transcript" in cap for cap in captions if isinstance(cap, dict))
                    transcript_status = "Transcript available" if has_transcript else "No transcript"
                
                self.output.insert(tk.END, f"{item_url:<60} | {item_title:<30} | {tags:<20} | {year:<6} | {transcript_status:<20}\n")
                
                # Add transcript preview if available
                if "youtube_captions" in item:
                    for cap in item["youtube_captions"]:
                        if isinstance(cap, dict) and "transcript" in cap:
                            transcript_text = cap["transcript"][:80] + "..." if len(cap.get("transcript", "")) > 80 else cap.get("transcript", "")
                            lang = cap.get("languageCode", "unknown")
                            self.output.insert(tk.END, f"  [{lang}] {transcript_text}\n")
                
                self.output.insert(tk.END, "-" * 150 + "\n")

            self.status_var.set(f"Done! Crawled {len(results)} pages")
        except Exception as e:
            self.output.insert(tk.END, f"✗ Error: {str(e)}\n")
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Crawl Error", str(e))
        finally:
            self.crawling = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.output.see(tk.END)

    def stop_crawl(self):
        self.crawling = False
        self.output.insert(tk.END, "\n[Crawl stopped by user]\n")
        self.status_var.set("Stopped")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def clear_results(self):
        self.output.delete(1.0, tk.END)
        self.status_var.set("Ready")


if __name__ == "__main__":
    root = tk.Tk()
    gui = CrawlerGUI(root)
    root.mainloop()
