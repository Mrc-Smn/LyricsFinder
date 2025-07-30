import os
import requests
from bs4 import BeautifulSoup
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.id3 import ID3NoHeaderError, ID3, USLT
import re
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import threading
import queue
import time
import random

# --- Global setup ---
message_queue = queue.Queue()
SUPPORTED_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg')
stop_event = threading.Event()

# A list of common User-Agents to rotate through, making requests less uniform.
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5.2 Safari/605.1.15',
]


def get_random_headers():
    """Creates a dictionary of headers that looks like a real browser request."""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/',
        'DNT': '1'
    }


def log_message(message):
    """Puts a message into the queue for the GUI to display."""
    message_queue.put(message)


# --- Search and Utility Functions ---

def clean_string(s):
    """Removes parenthetical and feature tags from a string for better searching."""
    if not s: return ""
    s = re.sub(r"[\(\[].*?[\)\]]", "", s)
    s = re.sub(r"\b(feat|ft|with|featuring)\b.*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[^\w\s'-]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def get_search_url(session, site, artist, title):
    """
    Scrapes a search engine and intelligently selects the most relevant URL.
    """
    query = f'site:{site} "{artist}" "{title}" lyrics'
    search_url = f"https://www.startpage.com/sp/search?q={requests.utils.quote(query)}"
    log_message(f"Searching with query: {search_url}")

    time.sleep(random.uniform(1.5, 3.0))

    try:
        response = session.get(search_url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        link_tags = soup.select("a.result-link")
        if not link_tags:
            log_message("✗ Direct scrape: No result links found on page.")
            return None

        # Prepare artist and title for smarter URL matching
        url_artist = re.sub(r"[^\w]", "", artist).lower()
        url_title = re.sub(r"[^\w]", "", title).lower()

        for link in link_tags:
            url = link.get('href')
            if url and url.startswith('http') and site in url:
                lower_url = url.lower()
                # *** THIS IS THE FIX: High-confidence matching logic ***
                # Check if the URL contains the artist and title, and isn't an album/artist page.
                if (url_artist in re.sub(r"[^\w]", "", lower_url) and
                        url_title in re.sub(r"[^\w]", "", lower_url) and
                        "album" not in lower_url and
                        "/artist/" not in lower_url):
                    log_message(f"✓ Found HIGH-CONFIDENCE URL: {url}")
                    return url  # Return the first good match

        log_message(f"✗ No high-confidence URL found for the site '{site}'.")

    except Exception as e:
        log_message(f"Error during direct scrape: {e}")
    return None


def scrape_lyrics(session, url):
    """Scrapes lyrics from a given URL using the provided session."""
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Try Genius structure first
        lyrics_divs = soup.select("div[data-lyrics-container='true']")
        if lyrics_divs:
            lyrics_text = "\n".join([div.get_text(separator='\n') for div in lyrics_divs]).strip()
            return re.sub(r'(\[.*?\]|\n\s*\n)', lambda m: '' if m.group(0).startswith('[') else '\n',
                          lyrics_text).strip()

        # Try Musixmatch structure
        lyrics_p = soup.select("p.mxm-lyrics__content")
        if lyrics_p:
            return "\n".join([p.get_text(separator='\n') for p in lyrics_p]).strip()

        # Try LyricFind structure
        lyrics_div = soup.find("div", id="lyrics")
        if lyrics_div:
            return lyrics_div.get_text(separator='\n').strip()

    except Exception as e:
        log_message(f"Error scraping page {url}: {e}")
    return ""


# --- File Processing Functions ---

def generate_lrc(lyrics):
    if not lyrics: return ""
    lines = []
    for i, line in enumerate(lyrics.splitlines()):
        if line.strip():
            minutes = i * 5 // 60
            seconds = i * 5 % 60
            lines.append(f"[{minutes:02d}:{seconds:02d}.00]{line}")
    return "\n".join(lines)


def get_audio_info(audio_path):
    artist, title = "", ""
    try:
        ext = os.path.splitext(audio_path)[1].lower()
        if ext == '.mp3':
            try:
                tags = EasyID3(audio_path)
            except ID3NoHeaderError:
                tags = ID3(audio_path)
            artist, title = tags.get("artist", [""])[0], tags.get("title", [""])[0]
        elif ext == '.m4a':
            tags = MP4(audio_path)
            artist, title = tags.get('\xa9ART', [""])[0], tags.get('\xa9nam', [""])[0]
        elif ext == '.flac':
            tags = FLAC(audio_path)
            artist, title = tags.get("artist", [""])[0], tags.get("title", [""])[0]
        elif ext == '.ogg':
            tags = OggVorbis(audio_path)
            artist, title = tags.get("artist", [""])[0], tags.get("title", [""])[0]
    except Exception as e:
        log_message(f"Couldn't read tags for {os.path.basename(audio_path)}: {e}")

    if not artist or not title:
        filename = os.path.splitext(os.path.basename(audio_path))[0]
        parts = filename.split(" - ", 1)
        artist = parts[0].strip() if len(parts) > 1 else "Unknown Artist"
        title = parts[1].strip() if len(parts) > 1 else filename.strip()
    return clean_string(artist), clean_string(title)


def has_embedded_lyrics(file_path):
    """Checks if a music file already has embedded lyrics."""
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.mp3':
            audio = ID3(file_path);
            return bool(audio.getall("USLT"))
        elif ext == '.m4a':
            audio = MP4(file_path);
            return '\xa9lyr' in audio
        elif ext == '.flac':
            audio = FLAC(file_path);
            return 'LYRICS' in audio
        elif ext == '.ogg':
            audio = OggVorbis(file_path);
            return 'LYRICS' in audio
    except Exception:
        return False
    return False


def embed_lyrics_into_file(file_path, lyrics):
    """Embeds lyrics into the metadata of a music file."""
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.mp3':
            audio = ID3(file_path)
            if audio.getall("USLT"): audio.delall("USLT")
            audio.add(USLT(encoding=3, text=lyrics))
        elif ext == '.m4a':
            audio = MP4(file_path);
            audio['\xa9lyr'] = lyrics
        elif ext == '.flac':
            audio = FLAC(file_path);
            audio['LYRICS'] = lyrics
        elif ext == '.ogg':
            audio = OggVorbis(file_path);
            audio['LYRICS'] = lyrics
        else:
            return False

        audio.save()
        log_message("✓ Lyrics embedded in music file.")
        return True
    except Exception as e:
        log_message(f"✗ Error embedding lyrics: {e}")
        return False


def process_audio_worker(folder, save_lrc, embed_lyrics, skip_existing):
    if not save_lrc and not embed_lyrics:
        log_message("No output options selected. Nothing to do.")
        message_queue.put("TASK_COMPLETE");
        return

    # Create a single session for the entire worker to maintain cookies and a consistent identity.
    with requests.Session() as session:
        session.headers.update(get_random_headers())

        audio_files = [os.path.join(r, f) for r, _, fs in os.walk(folder) for f in fs if
                       f.lower().endswith(SUPPORTED_EXTENSIONS) and not f.startswith('._')]

        if not audio_files:
            log_message(f"No supported audio files found in '{folder}'.")
            message_queue.put("TASK_COMPLETE");
            return

        log_message(f"Found {len(audio_files)} supported audio files to process...")
        for i, file_path in enumerate(audio_files, 1):
            if stop_event.is_set(): log_message("Scraping stopped by user."); break

            if embed_lyrics and skip_existing and has_embedded_lyrics(file_path):
                log_message(f"\n[{i}/{len(audio_files)}] Skipping {os.path.basename(file_path)} (lyrics exist).")
                continue

            file_name = os.path.basename(file_path)
            log_message(f"\n[{i}/{len(audio_files)}] Processing: {file_name}")
            artist, title = get_audio_info(file_path)
            if not title: log_message(f"Could not determine title for {file_name}. Skipping."); continue

            log_message(f"Searching for: {artist} - {title}")
            lyrics, source = "", ""
            SITES_TO_TRY = ["genius.com", "musixmatch.com", "lyrics.lyricfind.com"]

            for site in SITES_TO_TRY:
                log_message(f"--- Trying Source: {site} ---")
                found_url = get_search_url(session, site, artist, title)

                if found_url:
                    # Genius URLs are special and must contain "-lyrics" to be valid
                    if site == "genius.com" and "-lyrics" not in found_url:
                        log_message(f"✗ Found Genius URL is not a valid lyrics page: {found_url}")
                        continue  # Move to the next site

                    lyrics = scrape_lyrics(session, found_url)
                    if lyrics:
                        source = site.split('.')[0].capitalize()
                        break  # Found lyrics, so we can stop searching

            if lyrics:
                log_message(f"✓ Success! Lyrics found via {source}.")
                if save_lrc:
                    lrc_path = os.path.splitext(file_path)[0] + ".lrc"
                    lrc_content = generate_lrc(lyrics)
                    try:
                        with open(lrc_path, "w", encoding="utf-8") as f:
                            f.write(lrc_content)
                        log_message(f"✓ .lrc file saved: {os.path.basename(lrc_path)}")
                    except Exception as e:
                        log_message(f"✗ Error writing .lrc file: {e}")

                if embed_lyrics:
                    embed_lyrics_into_file(file_path, lyrics)
            else:
                log_message(f"✗ Failed: Could not find lyrics for {artist} - {title} from any source.")

    message_queue.put("TASK_COMPLETE")


# --- GUI Class ---

class LyricsScraperApp:
    def __init__(self, master):
        self.master = master
        master.title("Lyrics Scraper")
        master.geometry("700x550")
        self.processing_thread = None

        top_frame = tk.Frame(master)
        top_frame.pack(fill='x', padx=10, pady=(10, 5))
        tk.Label(top_frame, text="Music Folder:").pack(side='left')
        self.folder_path = tk.StringVar()
        tk.Entry(top_frame, textvariable=self.folder_path, state='readonly').pack(side='left', expand=True, fill='x',
                                                                                  padx=5)
        tk.Button(top_frame, text="Browse...", command=self.browse_folder).pack(side='left')

        options_frame = tk.Frame(master)
        options_frame.pack(pady=10, padx=10, fill='x')
        self.save_lrc = tk.BooleanVar(value=True)
        self.embed_lyrics = tk.BooleanVar(value=True)
        self.skip_existing = tk.BooleanVar(value=True)

        tk.Checkbutton(options_frame, text="Save as .lrc file", variable=self.save_lrc).pack(anchor='w')
        tk.Checkbutton(options_frame, text="Embed in music file", variable=self.embed_lyrics).pack(anchor='w')
        tk.Checkbutton(options_frame, text="Skip files with existing lyrics (if embedding)",
                       variable=self.skip_existing).pack(anchor='w', padx=(20, 0))

        button_frame = tk.Frame(master)
        button_frame.pack(pady=5)
        self.start_button = tk.Button(button_frame, text="Start Scraping", command=self.start_scraping)
        self.start_button.pack(side='left', padx=5)
        self.stop_button = tk.Button(button_frame, text="Stop", command=self.stop_scraping, state=tk.DISABLED)
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
        if not self.folder_path.get(): messagebox.showwarning("No Folder Selected",
                                                              "Please select your music folder first."); return
        if not self.save_lrc.get() and not self.embed_lyrics.get(): messagebox.showwarning("No Output Selected",
                                                                                           "Please select at least one output option."); return
        if self.processing_thread and self.processing_thread.is_alive(): messagebox.showinfo("In Progress",
                                                                                             "Scraping is already running."); return

        self.log_text.config(state='normal');
        self.log_text.delete(1.0, tk.END);
        self.log_text.config(state='disabled')
        stop_event.clear()
        self.status_label.config(text="Processing...")
        self.start_button.config(state=tk.DISABLED);
        self.stop_button.config(state=tk.NORMAL)

        self.processing_thread = threading.Thread(target=process_audio_worker, args=(
        self.folder_path.get(), self.save_lrc.get(), self.embed_lyrics.get(), self.skip_existing.get()))
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def stop_scraping(self):
        if self.processing_thread and self.processing_thread.is_alive():
            log_message("Stop request received. Finishing current song before stopping...")
            stop_event.set();
            self.stop_button.config(state=tk.DISABLED)

    def log_message_gui(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END);
        self.log_text.config(state='disabled')

    def check_queue(self):
        while not message_queue.empty():
            message = message_queue.get()
            if message == "TASK_COMPLETE":
                self.status_label.config(text="Done!")
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                if not stop_event.is_set():
                    messagebox.showinfo("Finished", "The scraping process has completed!")
                else:
                    messagebox.showinfo("Stopped", "The scraping process was stopped by the user.")
            else:
                self.log_message_gui(message)
        self.master.after(100, self.check_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = LyricsScraperApp(root)
    root.mainloop()
