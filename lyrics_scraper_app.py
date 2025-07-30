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
import lyricsgenius
from unidecode import unidecode

# --- Global setup ---
message_queue = queue.Queue()
SUPPORTED_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg')
stop_event = threading.Event()

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
]


def get_random_headers():
    return {'User-Agent': random.choice(USER_AGENTS)}


def log_message(message):
    message_queue.put(message)


# --- Search and Utility Functions ---

def clean_string(s):
    """Cleans metadata by removing feature tags and parentheticals."""
    if not s: return ""
    s = re.sub(r"[\(\[].*?[\)\]]", "", s)
    s = re.sub(r"\b(feat|ft|with|featuring)\b.*", "", s, flags=re.IGNORECASE)
    return s.strip()


def slugify(text):
    """Converts text to a URL-friendly slug."""
    text = unidecode(text).lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text


def search_genius_api(artist, title, api_key):
    """Searches for lyrics using the official Genius API."""
    log_message("--- Trying Source: Genius API ---")
    try:
        genius = lyricsgenius.Genius(api_key, verbose=False, remove_section_headers=True, timeout=15)
        song = genius.search_song(title, artist)
        if song:
            log_message("✓ Found song via Genius API.")
            lyrics = re.sub(r'.*?Lyrics', '', song.lyrics, 1)
            lyrics = re.sub(r'\d*Embed$', '', lyrics)
            return lyrics.strip()
    except Exception as e:
        log_message(f"✗ Genius API error: {e}")
    return None


def try_direct_url(session, site, artist, title):
    """Constructs and tests a direct URL for a given site."""
    log_message(f"--- Trying Direct URL for {site} ---")

    slug_artist = slugify(artist)
    slug_title = slugify(title)

    if not slug_artist or not slug_title:
        return None

    url_formats = {
        "genius.com": f"https://genius.com/{slug_artist}-{slug_title}-lyrics",
        "musixmatch.com": f"https://www.musixmatch.com/lyrics/{slug_artist}/{slug_title}",
        "lyrics.lyricfind.com": f"https://lyrics.lyricfind.com/lyrics/{slug_artist}-{slug_title}"
    }

    direct_url = url_formats.get(site)
    if not direct_url:
        return None

    log_message(f"Testing direct URL: {direct_url}")
    try:
        # Use a HEAD request for speed - we only need to know if the page exists.
        response = session.head(direct_url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            log_message("✓ Direct URL is valid.")
            return direct_url
        else:
            log_message(f"✗ Direct URL failed (Status: {response.status_code}).")
            return None
    except requests.RequestException:
        log_message("✗ Direct URL failed (Connection Error).")
        return None


def search_fallback(session, site, artist, title):
    """Scrapes Bing as a fallback to find the most relevant URL."""
    log_message(f"--- Fallback Search for {site} ---")
    query = f'site:{site} "{artist}" "{title}" lyrics'
    search_url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
    log_message(f"Searching with query: {search_url}")
    time.sleep(random.uniform(1.5, 3.0))

    try:
        response = session.get(search_url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        link_tags = soup.select("li.b_algo h2 a")
        if not link_tags:
            log_message("✗ Fallback scrape: No result links found on page.")
            return None

        for link in link_tags:
            url = link.get('href')
            if url and url.startswith('http') and site in url:
                log_message(f"✓ Found potential URL via fallback: {url}")
                return url  # Return the first result as the best guess

        log_message(f"✗ Fallback scrape: No links found for '{site}'.")
    except Exception as e:
        log_message(f"Error during fallback scrape: {e}")
    return None


def scrape_lyrics(session, url):
    """Scrapes lyrics from a given URL."""
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        lyrics_text = ""
        if "genius.com" in url:
            lyrics_divs = soup.select("div[data-lyrics-container='true']")
            if lyrics_divs: lyrics_text = "\n".join([div.get_text(separator='\n') for div in lyrics_divs])
        elif "musixmatch.com" in url:
            lyrics_p = soup.select("p.mxm-lyrics__content")
            if lyrics_p: lyrics_text = "\n".join([p.get_text(separator='\n') for p in lyrics_p])
        elif "lyrics.lyricfind.com" in url:
            lyrics_div = soup.find("div", id="lyrics")
            if lyrics_div: lyrics_text = lyrics_div.get_text(separator='\n')

        return re.sub(r'(\[.*?\]|\n\s*\n)', lambda m: '' if m.group(0).startswith('[') else '\n', lyrics_text).strip()
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


def process_audio_worker(folder, save_lrc, embed_lyrics, skip_existing, api_key):
    if not save_lrc and not embed_lyrics:
        log_message("No output options selected. Nothing to do.")
        message_queue.put("TASK_COMPLETE");
        return

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

            if api_key:
                lyrics = search_genius_api(artist, title, api_key)
                if lyrics: source = "Genius API"

            if not lyrics:
                SITES_TO_TRY = ["genius.com", "musixmatch.com", "lyrics.lyricfind.com"]
                for site in SITES_TO_TRY:
                    # First, try the direct URL method
                    found_url = try_direct_url(session, site, artist, title)
                    # If that fails, fall back to Bing search
                    if not found_url:
                        found_url = search_fallback(session, site, artist, title)

                    if found_url:
                        lyrics = scrape_lyrics(session, found_url)
                        if lyrics:
                            source = site.split('.')[0].capitalize() + " Scraper"
                            break

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
        master.geometry("700x600")
        self.processing_thread = None

        top_frame = tk.Frame(master)
        top_frame.pack(fill='x', padx=10, pady=(10, 5))
        tk.Label(top_frame, text="Music Folder:").pack(side='left')
        self.folder_path = tk.StringVar()
        tk.Entry(top_frame, textvariable=self.folder_path, state='readonly').pack(side='left', expand=True, fill='x',
                                                                                  padx=5)
        tk.Button(top_frame, text="Browse...", command=self.browse_folder).pack(side='left')

        api_frame = tk.LabelFrame(master, text="Genius API (Recommended)", padx=5, pady=5)
        api_frame.pack(pady=5, padx=10, fill='x')
        tk.Label(api_frame, text="API Key:").pack(side='left', padx=(0, 5))
        self.api_key = tk.StringVar()
        tk.Entry(api_frame, textvariable=self.api_key, width=60).pack(side='left', expand=True, fill='x')

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
        self.start_button = tk.Button(button_frame, text="Start Processing", command=self.start_scraping)
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
                                                                                             "Processing is already running."); return

        self.log_text.config(state='normal');
        self.log_text.delete(1.0, tk.END);
        self.log_text.config(state='disabled')
        stop_event.clear()
        self.status_label.config(text="Processing...")
        self.start_button.config(state=tk.DISABLED);
        self.stop_button.config(state=tk.NORMAL)

        api_key_val = self.api_key.get().strip()
        self.processing_thread = threading.Thread(target=process_audio_worker, args=(
        self.folder_path.get(), self.save_lrc.get(), self.embed_lyrics.get(), self.skip_existing.get(), api_key_val))
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
                    messagebox.showinfo("Finished", "The process has completed!")
                else:
                    messagebox.showinfo("Stopped", "The process was stopped by the user.")
            else:
                self.log_message_gui(message)
        self.master.after(100, self.check_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = LyricsScraperApp(root)
    root.mainloop()
