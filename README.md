Lyrics Scraper
A simple yet powerful desktop application to automatically find and save lyrics for your local music collection.

Features
Automatic Metadata Reading: Extracts artist and title information directly from your music files (.mp3, .m4a, .flac, .ogg).

Multi-Source Scraping: Searches for lyrics from multiple popular sources (Genius, Musixmatch, and LyricFind) to ensure the best chance of success.

Flexible Output:

Save as .lrc file: Creates a separate, timed lyrics file in the same directory as the song.

Embed in Music File: Writes the lyrics directly into the song's metadata tags, viewable in apps like Apple Music, VLC, and more.

Smart and Safe: Includes an option to skip files that already have embedded lyrics, preventing accidental overwrites.

User-Friendly Interface: A simple and clean GUI built with Tkinter.

Getting Started
1. Using the Pre-built Application
The easiest way to get started is to download the latest pre-built application for your operating system from the Releases page.

No installation is needed. Just download the file, unzip it, and run the Lyrics Scraper application.

2. Running from Source
If you prefer to run the application from the source code, you will need Python 3 installed.

Clone the repository:

git clone https://github.com/Mrc-Smn/LyricsFinder.git
cd LyricsFinder

Install the required dependencies:

pip install -r requirements.txt

Run the application:

python lyrics_scraper_app.py

How to Build Your Own Executable
You can package the application into a standalone executable using PyInstaller.

Install PyInstaller:

pip install pyinstaller

Run the Build Command:

For macOS:

pyinstaller --onefile --windowed --name="Lyrics Scraper" --icon="icon.icns" lyrics_scraper_app.py

For Windows:

pyinstaller --onefile --windowed --name="Lyrics Scraper" --icon="icon.ico" lyrics_scraper_app.py

The final application will be located in the dist folder.