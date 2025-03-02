import requests
import time

def check_url(url):
    try:
        print(f"Checking URL: {url}")
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.text)} bytes")
        print(f"Content Type: {response.headers.get('Content-Type', 'Unknown')}")
        
        # Print first 500 characters of content
        print("\nContent Preview:")
        print("-" * 50)
        print(response.text[:500])
        print("-" * 50)
        
        # Save the full response for inspection
        with open("vidsrc_icu_response.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"Full response saved to vidsrc_icu_response.html")
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def check_embed_url(content_id, content_type="movie"):
    embed_url = f"https://vidsrc.icu/embed/{content_type}/{content_id}"
    return check_url(embed_url)

if __name__ == "__main__":
    # Check main site
    main_site_ok = check_url("https://vidsrc.icu/")
    print(f"\nMain site accessible: {main_site_ok}")
    
    # Wait a bit
    time.sleep(2)
    
    # Check embed URL for a movie
    movie_embed_ok = check_embed_url("299534")  # Avengers: Endgame
    print(f"\nMovie embed accessible: {movie_embed_ok}") 