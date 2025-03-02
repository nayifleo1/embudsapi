# Vidsrc.icu Stream Link Extractor

This script helps extract direct stream links from vidsrc.icu for movies, TV shows, anime, and manga content.

## Features

- Supports multiple content types:
  - Movies
  - TV Shows (with season/episode selection)
  - Anime (with sub/dub options)
  - Manga (by chapter)
- Provides direct stream links in various formats (HLS, MP4)
- Extracts subtitle tracks when available
- Offers two extraction methods:
  - Direct API method (fast, non-browser based)
  - Browser-based extraction (fallback, more robust)
- Smart quality detection

## Requirements

- Python 3.7+
- Chrome browser installed
- Required Python packages (install using requirements.txt)

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

2. Make sure you have Chrome browser installed on your system.

## Usage

### Command Line

The script can be used directly from the command line:

```bash
# For movies
python vidsrc_icu_extractor.py --id 310131 --type movie

# For TV shows
python vidsrc_icu_extractor.py --id 88396 --type tv --season 1 --episode 1

# For anime
python vidsrc_icu_extractor.py --id 131681 --type anime --episode 1 --dub 0

# Force browser-based extraction
python vidsrc_icu_extractor.py --id 310131 --type movie --browser

# Run in headless mode
python vidsrc_icu_extractor.py --id 310131 --type movie --headless
```

### As a Module in Your Code

```python
from vidsrc_icu_extractor import VidsrcIcuExtractor

# Create the extractor
extractor = VidsrcIcuExtractor(headless=True)

# Extract movie streams
movie_result = extractor.get_content_links('movie', '310131')

# Extract TV show streams
tv_result = extractor.get_content_links('tv', '88396', season=1, episode=1)

# Extract anime streams
anime_result = extractor.get_content_links('anime', '131681', episode=1, dub=0)

# Print the results
for stream in movie_result['streams']:
    print(f"[{stream['type']} - {stream['quality']}] {stream['url']}")

for subtitle in movie_result['subtitles']:
    print(f"[{subtitle['language']}] {subtitle['label']}: {subtitle['src']}")
```

## Command Line Arguments

| Argument | Description |
|----------|-------------|
| `--id` | TMDB or IMDB ID of the content (required) |
| `--type` | Type of content: movie, tv, anime, or manga (default: movie) |
| `--season` | Season number (required for TV shows) |
| `--episode` | Episode number (required for TV shows and anime) or chapter (for manga) |
| `--dub` | Dub option for anime: 0 for sub, 1 for dub |
| `--browser` | Force browser-based extraction even if direct API method might work |
| `--headless` | Run browser in headless mode (no visible window) |

## How It Works

1. The script first attempts to extract sources using the direct API method:
   - Fetches the embed page directly using requests
   - Parses the HTML to find stream links and subtitles
   - Extracts links from script tags and regex patterns

2. If the direct method fails, it falls back to using a browser:
   - Uses undetected-chromedriver to bypass anti-bot measures
   - Interacts with the page to activate video players
   - Extracts stream links from various sources (network requests, page elements)
   - Handles iframes and multiple video sources

## Note

This script is for educational purposes only. Please respect the terms of service of the websites you interact with and ensure you have the right to access the content. 