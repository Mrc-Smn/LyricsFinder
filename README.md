# LyricsFinder

A Python desktop app to find and download lyrics for your local audio files and save them as .lrc files.

## Features

-   Fetches lyrics from Genius.com using their official API.
-   Uses scraping as a fallback if the API fails.
-   Supports MP3, FLAC, M4A, and OGG files.
-   Simple graphical user interface.

## Setup

1.  Clone the repository.
2.  Install the required libraries:
    `pip install -r requirements.txt`
3.  Create a `.env` file in the root directory.
4.  Add your Genius API key to the `.env` file:
    `GENIUS_API_KEY="YOUR_KEY_HERE"`

## Usage

Run the application with:
`python lyrics_scraper_app.py`