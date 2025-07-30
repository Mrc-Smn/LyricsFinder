Lyrics Scraper
A robust, hybrid desktop application to automatically find and save lyrics for your local music collection using both the official Genius API and a powerful scraping engine.

Note: Replace with an updated screenshot of the final UI.

Features
Hybrid Search: Uses the fast and reliable official Genius API as the primary method and automatically falls back to a powerful scraping engine if no API key is provided.

Intelligent Scraping Fallback:

Direct URL Guessing: First attempts to construct and verify a direct URL to the lyrics page for maximum speed and accuracy.

Smart Search: If the direct guess fails, it uses a search engine to find the most relevant link, with intelligent scoring to avoid incorrect matches.

Multi-Source Scraping: The scraping engine checks Genius, Musixmatch, and LyricFind to ensure the best chance of success.

Flexible Output:

Save as .lrc file: Creates a separate, timed lyrics file in the same directory as the song.

Embed in Music File: Writes the lyrics directly into the song's metadata tags.

Smart and Safe: Includes an option to skip files that already have embedded lyrics, preventing accidental overwrites.

Cross-Platform: Built with a clean Tkinter GUI that works on both macOS and Windows.

Getting Started
1. Using the Pre-built Application (Recommended)
The easiest way to get started is to download the latest pre-built application for your operating system from the Releases Page on GitHub.

No installation is needed. Just download the file (.zip for macOS, .exe for Windows), and run the Lyrics Scraper application.

2. Running from Source
If you prefer to run the application from the source code, you will need Python 3 installed.

Clone the repository:

git clone https://github.com/Mrc-Smn/LyricsFinder.git
cd LyricsFinder

Install the required dependencies:

pip install -r requirements.txt

Run the application:

python lyrics_scraper_app.py

Genius API Key (Optional but Recommended)
For the best performance and accuracy, it is highly recommended to use the Genius API.

Sign up for a free API key at https://genius.com/api-clients.

Copy the Client Access Token.

Paste this key into the API key field in the application.

If you do not provide a key, the application will automatically use the scraping engine.

How to Build Your Own Executable
You can package the application into a standalone executable using PyInstaller.

Install PyInstaller:

pip install pyinstaller

Run the Build Command:

For macOS:

pyinstaller --onefile --windowed --name="Lyrics Scraper" --icon="icon.icns" lyrics_scraper_app.py

For Windows:

python -m pyinstaller --onefile --windowed --name="Lyrics Scraper" --icon="icon.ico" lyrics_scraper_app.py

The final application will be located in the dist folder.