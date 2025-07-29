import os
import requests
from bs4 import BeautifulSoup
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.id3 import ID3NoHeaderError
import re
import urllib.parse
import time
from urllib.parse import urlparse, parse_qs, unquote
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import threading
import queue
import lyricsgenius
from dotenv import load_dotenv
from ddgs.ddgs import DDGS
import sys

# --- Global setup ---
message_queue = queue.Queue()
SUPPORTED_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg', '.wav', '.aiff')
stop_event = threading.Event()


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def log_message(message):
    message_queue.put(message)


# --- Search and Utility Functions ---

def search_genius_api(artist, title):
    """Search for lyrics using the official Genius API."""
    log_message("Trying Genius API...")
    try:
        api_key = os.getenv("GENIUS_API_KEY")
        if not api_key:
            log_message("API Error: GENIUS_API_KEY not set.")
            return None
        genius = lyricsgenius.Genius(api_key, verbose=False, remove_section_headers=True, skip_non_songs=True)
        song = genius.search_song(title, artist)
        if song:
            log_message("✓ Found lyrics via Genius API.")
            return re.sub(r'(\d*EmbedShare URLCopyEmbedCopy|\d*Embed$)', '', song.lyrics).strip()
        else:
            log_message("Genius API did not find a match.")
    except Exception as e:
        log_message(f"Genius API error: {e}")
    return None


def clean_string(s):
    if not s: return ""
    s = re.sub(r"[\(\[].*?[\)\]]", "", s)
    s = re.sub(r"\b(feat|ft|with|featuring)\b.*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[^\w\s'-]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def search_genius_direct(artist, title):
    """Fallback search directly on Genius website."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    query = f"{artist} {title}".strip()
    search_url = f"https://genius.com/search?q={urllib.parse.quote_plus(query)}"
    try:
        log_message(f"Searching Genius directly: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            link = soup.select_one('a[href*="/lyrics"]')
            if link and 'genius.com' in link.get('href', ''):
                url = link['href']
                if "-lyrics" in url:
                    log_message(f"Found potential match: {url}")
                    return url
    except Exception as e:
        log_message(f"Error with Genius direct search: {e}")
    return None


def search_genius_duckduckgo(artist, title):
    """Fallback search using the ddgs library for reliability."""
    query = f'"{artist}" "{title}" site:genius.com'
    log_message(f"Trying DuckDuckGo library search: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            for result in results:
                if 'href' in result and 'genius.com' in result['href']:
                    url = result['href']
                    if "-lyrics" in url:
                        log_message(f"Found Genius URL via DDGS library: {url}")
                        return url
        log_message("DDGS library found no relevant Genius links.")
    except Exception as e:
        log_message(f"Error with ddgs library: {e}")
    return None


def scrape_genius_lyrics(url):
    """Scrape lyrics from a Genius URL with improved headers."""
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        lyrics_divs = soup.select("div[data-lyrics-container='true']")
        if lyrics_divs:
            lyrics_text = "\n".join([div.get_text(separator='\n') for div in lyrics_divs]).strip()
            return re.sub(r'(\[.*?\]|\n\s*\n)', lambda m: '' if m.group(0).startswith('[') else '\n',
                          lyrics_text).strip()
    except Exception as e:
        log_message(f"Error scraping Genius page {url}: {e}")
    return ""


def generate_lrc(lyrics):
    if not lyrics: return ""
    lines = [f"[{i * 5 // 60:02d}:{i * 5 % 60:02d}.00]{line}" for i, line in enumerate(lyrics.splitlines()) if
             line.strip()]
    return "\n".join(lines)


def get_audio_info(audio_path):
    artist, title = "", ""
    try:
        ext = os.path.splitext(audio_path)[1].lower()
        if ext == '.mp3':
            try:
                tags = EasyID3(audio_path)
                artist, title = tags.get("artist", [""])[0], tags.get("title", [""])[0]
            except ID3NoHeaderError:
                tags = ID3(audio_path)
                artist, title = tags.get("TPE1", [""])[0], tags.get("TIT2", [""])[0]
        elif ext == '.m4a':
            tags = MP4(audio_path)
            artist, title = tags.get('\xa9ART', [""])[0], tags.get('\xa9nam', [""])[0]
        elif ext == '.flac':
            tags = FLAC(audio_path)
            artist, title = tags.get("artist", [""])[0], tags.get("title", [""])[0]
        elif ext == '.ogg':
            tags = OggVorbis(audio_path)
            artist, title = tags.get("artist", [""])[0], tags.get("title", [""])[0]
    except Exception:
        pass
    if not artist or not title:
        filename = os.path.splitext(os.path.basename(audio_path))[0]
        parts = filename.split(" - ", 1)
        artist = parts[0].strip() if len(parts) > 1 else "Unknown Artist"
        title = parts[1].strip() if len(parts) > 1 else filename.strip()
    return clean_string(artist), clean_string(title)


def process_mp3s_worker(folder):
    """Worker function to process audio files in a separate thread."""
    # --- MODIFIED: Added 'and not f.startswith("._")' to ignore macOS metadata files ---
    audio_files = [os.path.join(r, f) for r, _, fs in os.walk(folder) for f in fs if
                   f.lower().endswith(SUPPORTED_EXTENSIONS) and not f.startswith('._')]

    if not audio_files:
        log_message(f"No supported audio files found in '{folder}'.");
        message_queue.put("TASK_COMPLETE");
        return

    log_message(f"Found {len(audio_files)} valid audio files to process...")
    for i, file_path in enumerate(audio_files, 1):
        if stop_event.is_set():
            log_message("Scraping stopped by user.");
            break

        file_name, lrc_path = os.path.basename(file_path), os.path.splitext(file_path)[0] + ".lrc"
        if os.path.exists(lrc_path):
            log_message(f"[{i}/{len(audio_files)}] Skipping {file_name} (LRC exists)");
            continue

        log_message(f"\n[{i}/{len(audio_files)}] Processing: {file_name}")
        artist, title = get_audio_info(file_path)
        if not title:
            log_message(f"Could not get title from {file_name}. Skipping.");
            continue

        log_message(f"Searching lyrics for: {artist} - {title}")

        lyrics = search_genius_api(artist, title)

        if not lyrics:
            log_message("API failed, falling back to scraping methods...")
            url = search_genius_direct(artist, title)
            if not url:
                url = search_genius_duckduckgo(artist, title)

            if url:
                log_message(f"Found valid Genius URL: {url}")
                lyrics = scrape_genius_lyrics(url)
            else:
                log_message("All scraping methods failed to find a valid URL.")

        if lyrics:
            lrc_content = generate_lrc(lyrics)
            try:
                with open(lrc_path, "w", encoding="utf-8") as f:
                    f.write(lrc_content)
                log_message(f"✓ Lyrics saved to {os.path.basename(lrc_path)}")
            except Exception as e:
                log_message(f"Error writing LRC file: {e}")
        else:
            log_message("Could not find lyrics for this song.")
        time.sleep(1)

    message_queue.put("TASK_COMPLETE")


class LyricsScraperApp:
    def __init__(self, master):
        self.master = master
        master.title("Genius LRC Scraper");
        master.geometry("700x500")
        self.folder_path = tk.StringVar()
        self.processing_thread = None

        tk.Label(master, text="Music Folder:").pack(pady=(10, 0))
        frame = tk.Frame(master);
        frame.pack(fill='x', padx=10)
        tk.Entry(frame, textvariable=self.folder_path).pack(side='left', expand=True, fill='x', padx=(0, 5))
        tk.Button(frame, text="Browse", command=self.browse_folder).pack(side='left')

        button_frame = tk.Frame(master);
        button_frame.pack(pady=5)
        self.start_button = tk.Button(button_frame, text="Start Scraping", command=self.start_scraping)
        self.start_button.pack(side='left', padx=5)
        self.stop_button = tk.Button(button_frame, text="Stop Scraping", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_button.pack(side='left', padx=5)

        self.log_text = scrolledtext.ScrolledText(master, wrap=tk.WORD, height=20)
        self.log_text.pack(expand=True, fill='both', padx=10, pady=5)
        self.log_text.config(state='disabled')

        self.status_label = tk.Label(master, text="Ready", bd=1, relief=tk.SUNKEN, anchor='w')
        self.status_label.pack(side='bottom', fill='x')

        self.master.after(100, self.check_queue)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder: self.folder_path.set(folder); self.log_message_gui(f"Selected folder: {folder}")

    def start_scraping(self):
        if not self.folder_path.get(): messagebox.showwarning("No Folder",
                                                              "Please select a music folder first."); return
        if self.processing_thread and self.processing_thread.is_alive(): messagebox.showinfo("In Progress",
                                                                                             "Scraping is already in progress."); return

        self.log_text.config(state='normal');
        self.log_text.delete(1.0, tk.END);
        self.log_text.config(state='disabled')
        stop_event.clear()

        self.status_label.config(text="Processing...");
        self.start_button.config(state=tk.DISABLED);
        self.stop_button.config(state=tk.NORMAL)

        self.processing_thread = threading.Thread(target=process_mp3s_worker, args=(self.folder_path.get(),))
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def stop_scraping(self):
        if self.processing_thread and self.processing_thread.is_alive():
            log_message("Stop request received. Finishing current song...")
            stop_event.set()
            self.stop_button.config(state=tk.DISABLED)

    def log_message_gui(self, message):
        self.log_text.config(state='normal');
        self.log_text.insert(tk.END, message + "\n");
        self.log_text.see(tk.END);
        self.log_text.config(state='disabled')

    def check_queue(self):
        while not message_queue.empty():
            message = message_queue.get()
            if message == "TASK_COMPLETE":
                self.status_label.config(text="Done!")
                self.start_button.config(state=tk.NORMAL);
                self.stop_button.config(state=tk.DISABLED)
                if not stop_event.is_set():
                    messagebox.showinfo("Finished", "Scraping process has completed!")
                else:
                    messagebox.showinfo("Stopped", "Scraping process was stopped by the user.")
            else:
                self.log_message_gui(message)
        self.master.after(100, self.check_queue)


if __name__ == "__main__":
    load_dotenv(resource_path('.env'))
    root = tk.Tk()
    app = LyricsScraperApp(root)
    root.mainloop()