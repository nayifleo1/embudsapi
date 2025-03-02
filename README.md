# Vidsrc.me Stream Link Extractor

This script helps extract direct stream links from vidsrc.me for movies and TV shows.

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

1. Basic usage with the example script:
```bash
python vidsrc_extractor.py
```

2. To use in your own code:
```python
from vidsrc_extractor import VidsrcExtractor

extractor = VidsrcExtractor()
try:
    # For movies, use the IMDB ID
    movie_links = extractor.get_stream_links("tt0133093", "movie")
    
    # For TV shows
    tv_links = extractor.get_stream_links("tt0944947", "tv")
    
    print(movie_links)
finally:
    extractor.close_browser()
```

## Features

- Uses undetected-chromedriver to bypass anti-bot measures
- Extracts direct stream links from embedded players
- Supports both movies and TV shows
- Finds M3U8 stream links
- Handles multiple iframes and video sources

## Note

This script is for educational purposes only. Please respect the terms of service of the websites you interact with and ensure you have the right to access the content. 