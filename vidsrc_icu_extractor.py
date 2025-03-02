import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
import json
import re
from urllib.parse import urlparse, parse_qs, unquote, quote
import logging
import os
import shutil
import random
import base64
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def decode_base64_url(encoded_str):
    """Decode a base64 URL-safe string"""
    try:
        # Add padding if needed
        padding = 4 - (len(encoded_str) % 4)
        if padding != 4:
            encoded_str += '=' * padding
        
        # Convert URL-safe characters back to standard base64
        encoded_str = encoded_str.replace('-', '+').replace('_', '/')
        
        # Decode
        decoded = base64.b64decode(encoded_str).decode('utf-8')
        return decoded
    except Exception as e:
        logger.debug(f"Base64 decode error: {str(e)}")
        return None

class VidsrcIcuExtractor:
    def __init__(self, debug=False):
        """Initialize the VidsrcIcu extractor with optional debug logging."""
        # Configure logging
        self.logger = logging.getLogger('VidsrcIcuExtractor')
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Base URLs and patterns
        self.base_url = "https://vidsrc.icu"
        # Update to use the correct embed URL format found in the HTML response
        self.embed_url_format = "https://vidsrcme.vidsrc.icu/embed/{content_type}?tmdb={id}{season_episode}"
        self.logger.info(f"Initialized VidsrcIcuExtractor with base URL: {self.base_url}")
        self.driver = None
        self.headless = False
        self.wait_time = 10
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
        ]
        self.user_agent = random.choice(self.user_agents)
        self.stream_links = []
        self.subtitles = []
        self.domain = "https://vidsrc.icu"

    def wait_for_element_present(self, by, value, timeout=None):
        """Wait for an element to be present on the page"""
        if timeout is None:
            timeout = self.wait_time
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.debug(f"Timeout waiting for element {value} to be present")
            return None

    def wait_for_url_change(self, old_url, timeout=None):
        """Wait for the URL to change from the old URL"""
        if timeout is None:
            timeout = self.wait_time
            
        def url_changed(driver):
            return driver.current_url != old_url
            
        try:
            WebDriverWait(self.driver, timeout).until(url_changed)
            return True
        except TimeoutException:
            logger.debug(f"Timeout waiting for URL to change from {old_url}")
            return False

    def start_browser(self):
        """Initialize the undetected Chrome browser with advanced settings"""
        try:
            # Clear existing ChromeDriver data
            chrome_data_dir = os.path.expanduser('~\\appdata\\roaming\\undetected_chromedriver')
            if os.path.exists(chrome_data_dir):
                shutil.rmtree(chrome_data_dir, ignore_errors=True)
                logger.info("Cleared existing ChromeDriver data")
            
            # Set up performance logging capabilities
            caps = DesiredCapabilities.CHROME
            caps['goog:loggingPrefs'] = {'performance': 'ALL', 'browser': 'ALL', 'network': 'ALL'}
            
            options = uc.ChromeOptions()
            
            # Configure Chrome options
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-infobars')
            
            # Enhanced anti-bot evasion
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            options.add_argument("--disable-site-isolation-trials")
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--disable-blink-features=AutomationControlled")
            
            # Use a realistic user agent
            options.add_argument(f'--user-agent={self.user_agent}')
            
            if self.headless:
                options.add_argument('--headless=new')
            
            # Initialize Chrome instance
            self.driver = uc.Chrome(
                options=options,
                version_main=129,
                suppress_welcome=True,
                use_subprocess=True,
                desired_capabilities=caps
            )
            
            # Set window size
            self.driver.set_window_size(1920, 1080)
            
            # Setup CDP commands
            self.driver.execute_cdp_cmd('Network.enable', {})
            self.driver.execute_cdp_cmd('Page.enable', {})
            
            # Add custom headers
            self.driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
                'headers': {
                    'Referer': self.domain,
                    'Origin': self.domain,
                    'User-Agent': self.user_agent,
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
                }
            })
            
            # Execute stealth JS to evade detection
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                // Overwrite the 'webdriver' property to undefined
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Overwrite chrome driver related properties
                window.navigator.chrome = {
                    runtime: {}
                };
                
                // Remove automation-related attributes
                if (document.documentElement.hasAttribute('webdriver')) {
                    document.documentElement.removeAttribute('webdriver');
                }
                
                // Add randomized fingerprinting values
                const randomFP = {
                    gpu: ['NVIDIA GeForce RTX 3070', 'AMD Radeon RX 6800 XT', 'Intel Iris Xe Graphics'],
                    memory: ['8', '16', '32'],
                    cpuThreads: ['4', '8', '12', '16'],
                    timezone: ['UTC-5', 'UTC+1', 'UTC+8', 'UTC+0'],
                };
                
                // Add random values to Canvas fingerprints
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type) {
                    if (this.width > 16 && this.height > 16) {
                        const ctx = this.getContext('2d');
                        const pixels = ctx.getImageData(0, 0, 1, 1);
                        // Add slight random noise
                        pixels.data[0] = pixels.data[0] + Math.floor(Math.random() * 10) - 5;
                        pixels.data[1] = pixels.data[1] + Math.floor(Math.random() * 10) - 5;
                        pixels.data[2] = pixels.data[2] + Math.floor(Math.random() * 10) - 5;
                        ctx.putImageData(pixels, 0, 0);
                    }
                    return originalToDataURL.apply(this, arguments);
                };
                """
            })
            
            logger.info("Browser started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {str(e)}")
            raise

    def extract_sources_from_page(self):
        """Extract sources from the current page using multiple methods"""
        try:
            # Wait for content to load
            time.sleep(3)
            
            # Click any play buttons to activate media
            play_selectors = [
                '.jw-icon-display', '.plyr__control--overlaid', '.play-button', 
                '[class*="play"]', '[id*="play"]', '.vjs-big-play-button',
                '.ytp-large-play-button', 'button', '.btn'
            ]
            
            for selector in play_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        try:
                            # Skip hidden elements
                            if not element.is_displayed():
                                continue
                                
                            # Try to click
                            try:
                                element.click()
                            except:
                                try:
                                    ActionChains(self.driver).move_to_element(element).click().perform()
                                except:
                                    self.driver.execute_script("arguments[0].click();", element)
                                    
                            time.sleep(1)  # Wait briefly after click
                        except:
                            continue
                except:
                    continue
            
            # Extract from network logs
            logs = self.driver.get_log('performance')
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    
                    if log.get('method') == 'Network.responseReceived':
                        response = log.get('params', {}).get('response', {})
                        url = response.get('url', '')
                        
                        if self.is_valid_stream_url(url):
                            self.stream_links.append(url)
                except:
                    continue
            
            # Extract from page source
            page_source = self.driver.page_source
            
            # Check for video elements
            soup = BeautifulSoup(page_source, 'html.parser')
            
            for video in soup.find_all('video'):
                if video.get('src'):
                    src = video['src']
                    if src.startswith('http'):
                        self.stream_links.append(src)
                
                # Check source elements
                for source in video.find_all('source'):
                    if source.get('src'):
                        src = source['src']
                        if src.startswith('http'):
                            self.stream_links.append(src)
            
            # Extract from iframes
            for iframe in soup.find_all('iframe'):
                if iframe.get('src') and iframe['src'].startswith('http'):
                    iframe_src = iframe['src']
                    # Only follow media-related iframes
                    if any(x in iframe_src.lower() for x in ['embed', 'player', 'video']):
                        try:
                            # Store current URL
                            current_url = self.driver.current_url
                            
                            # Navigate to iframe
                            self.driver.get(iframe_src)
                            time.sleep(3)
                            
                            # Extract from this page
                            self.extract_sources_from_page()
                            
                            # Go back
                            self.driver.get(current_url)
                            time.sleep(1)
                        except:
                            # If anything fails, try to get back to original page
                            self.driver.get(current_url)
            
            # Search for stream patterns in page source
            patterns = [
                r'https?://[^\s<>"\']+?\.m3u8[^\s<>"\']*',
                r'https?://[^\s<>"\']+?\.mp4[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/manifest[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/playlist[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/source[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/stream[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/hls[^\s<>"\']*',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_source)
                for match in matches:
                    if self.is_valid_stream_url(match):
                        self.stream_links.append(match)
            
            # Check page for JavaScript variables that might contain URLs
            js_extract = """
                function findStreams() {
                    const results = [];
                    
                    // Search in common variable names
                    const varNames = ['player', 'config', 'source', 'sources', 'stream', 'video', 'media',
                                     'playerConfig', 'videoSrc', 'url', 'streamUrl', 'streams'];
                    
                    for (const name of varNames) {
                        try {
                            if (window[name]) {
                                // Check if it's a string URL
                                if (typeof window[name] === 'string' && 
                                    window[name].match(/^https?:\\/\\/.*(m3u8|mp4|stream)/i)) {
                                    results.push(window[name]);
                                }
                                // Check if it's an object with URLs
                                else if (typeof window[name] === 'object') {
                                    // Look for properties that might contain URLs
                                    for (const prop in window[name]) {
                                        try {
                                            const value = window[name][prop];
                                            if (typeof value === 'string' && 
                                                value.match(/^https?:\\/\\/.*(m3u8|mp4|stream)/i)) {
                                                results.push(value);
                                            }
                                        } catch (e) {
                                            // Skip errors
                                        }
                                    }
                                }
                            }
                        } catch (e) {
                            // Skip errors
                        }
                    }
                    
                    // Look for sources in video players
                    const jwPlayer = document.querySelector('.jwplayer');
                    if (jwPlayer && window.jwplayer) {
                        try {
                            const player = window.jwplayer(jwPlayer.id);
                            const sources = player.getPlaylist()[0].sources;
                            for (const source of sources) {
                                if (source.file) {
                                    results.push(source.file);
                                }
                            }
                        } catch (e) {
                            // Skip errors
                        }
                    }
                    
                    // Look for HTML5 video sources
                    document.querySelectorAll('video').forEach(video => {
                        if (video.src) {
                            results.push(video.src);
                        }
                        video.querySelectorAll('source').forEach(source => {
                            if (source.src) {
                                results.push(source.src);
                            }
                        });
                    });
                    
                    return [...new Set(results)];
                }
                return findStreams();
            """
            
            try:
                js_results = self.driver.execute_script(js_extract)
                if js_results and isinstance(js_results, list):
                    for url in js_results:
                        if url and isinstance(url, str) and self.is_valid_stream_url(url):
                            self.stream_links.append(url)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error extracting sources from page: {str(e)}")

    def extract_subtitles_from_page(self):
        """Extract subtitles from the page"""
        try:
            # Check for track elements
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Look for track elements
            for track in soup.find_all('track'):
                if track.get('src') and track.get('kind') in ['subtitles', 'captions']:
                    subtitle = {
                        'kind': track.get('kind', 'subtitles'),
                        'src': track['src'],
                        'label': track.get('label', 'Unknown'),
                        'language': track.get('srclang', 'unknown')
                    }
                    self.subtitles.append(subtitle)
            
            # Look for subtitles in JW Player config
            js_extract = """
                function findSubtitles() {
                    const results = [];
                    
                    // JW Player
                    const jwPlayer = document.querySelector('.jwplayer');
                    if (jwPlayer && window.jwplayer) {
                        try {
                            const player = window.jwplayer(jwPlayer.id);
                            const tracks = player.getPlaylist()[0].tracks;
                            if (tracks) {
                                for (const track of tracks) {
                                    if (track.kind === 'captions' || track.kind === 'subtitles') {
                                        results.push({
                                            kind: track.kind,
                                            src: track.file,
                                            label: track.label,
                                            language: track.language || 'unknown'
                                        });
                                    }
                                }
                            }
                        } catch (e) {
                            // Skip errors
                        }
                    }
                    
                    // HTML5 Video tracks
                    document.querySelectorAll('video').forEach(video => {
                        video.querySelectorAll('track').forEach(track => {
                            if (track.kind === 'subtitles' || track.kind === 'captions') {
                                results.push({
                                    kind: track.kind,
                                    src: track.src,
                                    label: track.label,
                                    language: track.srclang || 'unknown'
                                });
                            }
                        });
                    });
                    
                    return results;
                }
                return findSubtitles();
            """
            
            try:
                js_results = self.driver.execute_script(js_extract)
                if js_results and isinstance(js_results, list):
                    for subtitle in js_results:
                        if subtitle and isinstance(subtitle, dict) and subtitle.get('src'):
                            self.subtitles.append(subtitle)
            except:
                pass
                
            # Check for subtitle URLs in page source
            subtitle_patterns = [
                r'https?://[^\s<>"\']+?\.vtt[^\s<>"\']*',
                r'https?://[^\s<>"\']+?\.srt[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/subtitles[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/captions[^\s<>"\']*'
            ]
            
            for pattern in subtitle_patterns:
                matches = re.findall(pattern, page_source)
                for match in matches:
                    self.subtitles.append({
                        'kind': 'subtitles',
                        'src': match,
                        'label': 'Auto-detected',
                        'language': 'unknown'
                    })
                    
        except Exception as e:
            logger.error(f"Error extracting subtitles from page: {str(e)}")

    def extract_from_direct_api(self, content_type, content_id, season=None, episode=None, dub=None):
        """
        Try to extract stream links directly using API calls without browser
        
        Args:
            content_type: 'movie', 'tv', 'anime', or 'manga'
            content_id: ID of the content from IMDB or TMDB
            season: Season number (for TV shows)
            episode: Episode number (for TV shows and anime)
            dub: Dub option for anime (0 for sub, 1 for dub)
            
        Returns:
            Dictionary with sources and subtitles
        """
        try:
            # Create a fresh session
            self.session = requests.Session()
            
            # Set common headers
            self.session.headers.update({
                'User-Agent': self.user_agent,
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            })
            
            # First visit the main domain to establish a session with cookies
            logger.info(f"Accessing main domain to establish session: {self.domain}")
            main_response = self.session.get(self.domain, timeout=10)
            
            if main_response.status_code != 200:
                logger.error(f"Failed to access main domain: {main_response.status_code}")
                return {'sources': [], 'subtitles': []}
                
            # Set the Referer header after visiting the main domain
            self.session.headers.update({
                'Referer': self.domain,
                'Origin': self.domain
            })
            
            # Generate the embed URL using our method
            embed_url = self.generate_embed_url(content_type, content_id, season, episode)
            
            logger.info(f"Requesting embed URL: {embed_url}")
            
            # Get the embed page
            response = self.session.get(embed_url, timeout=10)
            
            # Log detailed response information
            logger.debug(f"Response Status: {response.status_code}")
            logger.debug(f"Response Headers: {response.headers}")
            
            if response.status_code != 200:
                logger.error(f"Failed to get embed page: {response.status_code}")
                return {'sources': [], 'subtitles': []}
                
            html_content = response.text
            
            # Log the length of the HTML content
            logger.debug(f"HTML Content Length: {len(html_content)} bytes")
            
            # Log a preview of the HTML content
            logger.debug(f"HTML Content Preview: {html_content[:500]}...")
            
            # Debug - save the HTML content for inspection
            try:
                with open('vidsrc_icu_debug.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.debug(f"Saved debug HTML to vidsrc_icu_debug.html")
            except Exception as e:
                logger.debug(f"Failed to save debug HTML: {str(e)}")
            
            # Parse the HTML to find source information
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Detailed logging for soup content
            logger.debug(f"Title of page: {soup.title.string if soup.title else 'No title found'}")
            
            # Log all iframes found
            iframes = soup.find_all('iframe')
            if iframes:
                logger.debug(f"Found {len(iframes)} iframes in HTML")
                for i, iframe in enumerate(iframes):
                    logger.debug(f"Iframe {i+1}: {iframe.get('src', 'No src')} (id: {iframe.get('id', 'No id')})")
            else:
                logger.debug("No iframes found in HTML")
                
            # Log all video elements found
            videos = soup.find_all('video')
            if videos:
                logger.debug(f"Found {len(videos)} video elements in HTML")
                for i, video in enumerate(videos):
                    logger.debug(f"Video {i+1}: {video.get('src', 'No src')} (id: {video.get('id', 'No id')})")
            else:
                logger.debug("No video elements found in HTML")
            
            # Look for source information in script tags
            sources = []
            subtitles = []
            
            # Look for video player sections first
            player_divs = soup.select('.video-player, #player, #video-player, .player-container, .vidsrc-player')
            if player_divs:
                logger.debug(f"Found {len(player_divs)} potential player divs")
            
            # Check for iframes (common embedding method)
            for iframe in soup.find_all('iframe'):
                if iframe.get('src'):
                    src = iframe['src']
                    if src.startswith('//'):
                        src = 'https:' + src
                    logger.debug(f"Found iframe with src: {src}")
                    
                    if src.startswith('http'):
                        try:
                            # Get the iframe content
                            iframe_response = self.session.get(src, timeout=10)
                            if iframe_response.status_code == 200:
                                iframe_html = iframe_response.text
                                
                                # Look for stream URLs in iframe HTML
                                for pattern in [r'https?://[^\s<>"\']+?\.m3u8[^\s<>"\']*', 
                                               r'https?://[^\s<>"\']+?\.mp4[^\s<>"\']*']:
                                    matches = re.findall(pattern, iframe_html)
                                    for url in matches:
                                        if self.is_valid_stream_url(url):
                                            sources.append({
                                                'file': url,
                                                'type': 'mp4' if '.mp4' in url else 'hls',
                                                'quality': 'auto'
                                            })
                                            logger.debug(f"Found stream URL in iframe: {url}")
                        except Exception as e:
                            logger.debug(f"Error fetching iframe content: {str(e)}")
            
            # Try to find source data in script tags
            for script in soup.find_all('script'):
                script_text = script.string
                if not script_text:
                    continue
                
                # Look for direct source definitions in common patterns
                source_patterns = [
                    r'sources:\s*(\[.+?\])',
                    r'sources\s*=\s*(\[.+?\])',
                    r'"sources":\s*(\[.+?\])',
                    r'sources\s*:\s*(\[.*?\])',
                    r'file\s*:\s*["\'](.+?)["\']',
                    r'file["\']\s*:\s*["\'](.+?)["\']',
                    r'"file"\s*:\s*"(.+?)"',
                    r"file\s*:\s*'(.+?)'"
                ]
                
                for pattern in source_patterns:
                    source_matches = re.findall(pattern, script_text, re.DOTALL)
                    for match in source_matches:
                        try:
                            # If it's a JSON array
                            if match.startswith('['):
                                # Clean up the JSON (remove potential JS syntax)
                                json_str = match.replace("'", '"')
                                json_str = re.sub(r'(\w+):', r'"\1":', json_str)  # Add quotes to keys
                                
                                try:
                                    sources_data = json.loads(json_str)
                                    for source in sources_data:
                                        if isinstance(source, dict):
                                            file = source.get('file')
                                            if file and isinstance(file, str) and file.startswith('http'):
                                                sources.append({
                                                    'file': file,
                                                    'type': source.get('type', 'mp4' if '.mp4' in file else 'hls' if '.m3u8' in file else 'unknown'),
                                                    'quality': source.get('label', 'auto')
                                                })
                                                logger.debug(f"Found source in JSON array: {file}")
                                except json.JSONDecodeError:
                                    logger.debug(f"Failed to parse JSON: {json_str}")
                            
                            # If it's a direct URL
                            elif match.startswith('http'):
                                url = match
                                if self.is_valid_stream_url(url):
                                    sources.append({
                                        'file': url,
                                        'type': 'mp4' if '.mp4' in url else 'hls' if '.m3u8' in url else 'unknown',
                                        'quality': 'auto'
                                    })
                                    logger.debug(f"Found direct URL in script: {url}")
                        except Exception as e:
                            logger.debug(f"Error processing source match: {str(e)}")
                
                # Look for tracks/subtitles
                tracks_patterns = [
                    r'tracks:\s*(\[.+?\])',
                    r'tracks\s*=\s*(\[.+?\])',
                    r'"tracks":\s*(\[.+?\])',
                    r'tracks\s*:\s*(\[.*?\])'
                ]
                
                for pattern in tracks_patterns:
                    tracks_matches = re.findall(pattern, script_text, re.DOTALL)
                    for match in tracks_matches:
                        try:
                            # Clean up the JSON
                            json_str = match.replace("'", '"')
                            json_str = re.sub(r'(\w+):', r'"\1":', json_str)
                            
                            tracks_data = json.loads(json_str)
                            for track in tracks_data:
                                if track.get('file') and isinstance(track['file'], str) and track['file'].startswith('http'):
                                    if track.get('kind') in ['captions', 'subtitles']:
                                        subtitles.append({
                                            'kind': 'subtitles',
                                            'src': track['file'],
                                            'label': track.get('label', 'Unknown'),
                                            'language': track.get('language', 'unknown')
                                        })
                                        logger.debug(f"Found subtitle in tracks: {track['file']}")
                        except Exception as e:
                            logger.debug(f"Error parsing tracks JSON: {str(e)}")
                
                # Look for other direct source patterns in script text
                url_patterns = [
                    r'src\s*:\s*[\'"](.+?\.m3u8.*?)[\'"]',
                    r'src\s*:\s*[\'"](.+?\.mp4.*?)[\'"]',
                    r'url\s*:\s*[\'"](.+?\.m3u8.*?)[\'"]',
                    r'url\s*:\s*[\'"](.+?\.mp4.*?)[\'"]',
                    r'source\s*:\s*[\'"](.+?\.m3u8.*?)[\'"]',
                    r'source\s*:\s*[\'"](.+?\.mp4.*?)[\'"]',
                    r'"src"\s*:\s*"(.+?\.m3u8.*?)"',
                    r'"src"\s*:\s*"(.+?\.mp4.*?)"'
                ]
                
                for pattern in url_patterns:
                    url_matches = re.findall(pattern, script_text)
                    for url in url_matches:
                        if url.startswith('http') and self.is_valid_stream_url(url):
                            sources.append({
                                'file': url,
                                'type': 'mp4' if '.mp4' in url else 'hls' if '.m3u8' in url else 'unknown',
                                'quality': 'auto'
                            })
                            logger.debug(f"Found direct source URL: {url}")
            
            # If we found sources, return them
            if sources:
                logger.info(f"Found {len(sources)} sources and {len(subtitles)} subtitles using direct API method")
                return {
                    'sources': sources,
                    'subtitles': subtitles
                }
                
            # Try looking for player initialization
            player_init_patterns = [
                r'player\s*\(\s*{\s*(?:.*?)source\s*:\s*[\'"](.*?)[\'"]',
                r'player\s*\(\s*{\s*(?:.*?)file\s*:\s*[\'"](.*?)[\'"]',
                r'setup\s*\(\s*{\s*(?:.*?)file\s*:\s*[\'"](.*?)[\'"]',
                r'init\s*\(\s*{(?:.*?)file\s*:\s*[\'"](.*?)[\'"]'
            ]
            
            for pattern in player_init_patterns:
                matches = re.findall(pattern, html_content, re.DOTALL)
                for url in matches:
                    if url.startswith('http') and self.is_valid_stream_url(url):
                        sources.append({
                            'file': url,
                            'type': 'mp4' if '.mp4' in url else 'hls' if '.m3u8' in url else 'unknown',
                            'quality': 'auto'
                        })
                        logger.debug(f"Found URL in player initialization: {url}")
            
            # Try looking for direct URL patterns in the HTML
            stream_patterns = [
                r'https?://[^\s<>"\']+?\.m3u8[^\s<>"\']*',
                r'https?://[^\s<>"\']+?\.mp4[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/manifest[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/playlist[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/stream[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/hls[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/master[^\s<>"\']*'
            ]
            
            for pattern in stream_patterns:
                matches = re.findall(pattern, html_content)
                for url in matches:
                    if self.is_valid_stream_url(url):
                        sources.append({
                            'file': url,
                            'type': 'mp4' if '.mp4' in url else 'hls' if '.m3u8' in url else 'unknown',
                            'quality': 'auto'
                        })
                        logger.debug(f"Found stream URL in HTML: {url}")
            
            # Look for subtitle patterns
            subtitle_patterns = [
                r'https?://[^\s<>"\']+?\.vtt[^\s<>"\']*',
                r'https?://[^\s<>"\']+?\.srt[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/subtitles[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/captions[^\s<>"\']*'
            ]
            
            for pattern in subtitle_patterns:
                matches = re.findall(pattern, html_content)
                for url in matches:
                    subtitles.append({
                        'kind': 'subtitles',
                        'src': url,
                        'label': 'Auto-detected',
                        'language': 'unknown'
                    })
                    logger.debug(f"Found subtitle URL in HTML: {url}")
            
            # Return whatever we found
            if sources:
                logger.info(f"Found {len(sources)} sources and {len(subtitles)} subtitles")
            else:
                logger.warning("No sources found with direct API method")
                
            return {
                'sources': sources,
                'subtitles': subtitles
            }
            
        except Exception as e:
            logger.error(f"Error in extract_from_direct_api: {str(e)}")
            return {'sources': [], 'subtitles': []}

    def switch_to_iframe_and_extract(self, iframe_index=None, iframe_selector=None):
        """
        Switch to an iframe and attempt to extract content
        
        Args:
            iframe_index: Index of the iframe to switch to (0-based)
            iframe_selector: CSS selector for the iframe
            
        Returns:
            True if any sources were found
        """
        try:
            # Get current URL before switching
            current_url = self.driver.current_url
            
            # Find the iframe
            iframe = None
            if iframe_selector:
                try:
                    iframe = self.driver.find_element(By.CSS_SELECTOR, iframe_selector)
                    logger.debug(f"Found iframe with selector: {iframe_selector}")
                except:
                    logger.debug(f"Iframe with selector '{iframe_selector}' not found")
                    return False
            elif iframe_index is not None:
                iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                if iframes and len(iframes) > iframe_index:
                    iframe = iframes[iframe_index]
                    logger.debug(f"Found iframe at index: {iframe_index}")
                else:
                    logger.debug(f"No iframe at index {iframe_index}")
                    return False
            
            if not iframe:
                return False
            
            # Get iframe source
            try:
                iframe_src = iframe.get_attribute('src')
                logger.debug(f"Iframe source: {iframe_src}")
                if not iframe_src or iframe_src == 'about:blank' or not iframe_src.startswith('http'):
                    logger.debug("Iframe has empty or invalid src")
            except:
                logger.debug("Failed to get iframe src")
            
            # Switch to the iframe
            try:
                self.driver.switch_to.frame(iframe)
                logger.debug("Switched to iframe context")
            except Exception as e:
                logger.debug(f"Failed to switch to iframe: {str(e)}")
                return False
            
            # Wait for iframe content to load
            time.sleep(3)
            
            # Save a screenshot in iframe
            if logger.level <= logging.DEBUG:
                try:
                    iframe_name = iframe_index if iframe_index is not None else iframe_selector.replace(' ', '_')
                    filename = f'vidsrc_icu_iframe_{iframe_name}.png'
                    self.driver.save_screenshot(filename)
                    logger.debug(f"Saved iframe screenshot to {filename}")
                except:
                    pass
                
            # Extract sources and subtitles
            initial_stream_count = len(self.stream_links)
            self.extract_sources_from_page()
            self.extract_subtitles_from_page()
            
            # Check for nested iframes
            try:
                nested_iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                if nested_iframes:
                    logger.debug(f"Found {len(nested_iframes)} nested iframes")
                    
                    # Loop through nested iframes
                    for i, nested_iframe in enumerate(nested_iframes):
                        try:
                            nested_src = nested_iframe.get_attribute('src')
                            logger.debug(f"Nested iframe {i} src: {nested_src}")
                            
                            # Switch to the nested iframe
                            self.driver.switch_to.frame(nested_iframe)
                            logger.debug(f"Switched to nested iframe {i}")
                            
                            # Wait for content to load
                            time.sleep(2)
                            
                            # Extract from nested iframe
                            self.extract_sources_from_page()
                            self.extract_subtitles_from_page()
                            
                            # Switch back to parent iframe
                            self.driver.switch_to.parent_frame()
                        except:
                            # If anything fails, try to get back to the parent iframe
                            try:
                                self.driver.switch_to.parent_frame()
                            except:
                                pass
            except:
                pass
            
            # Switch back to main document
            try:
                self.driver.switch_to.default_content()
                logger.debug("Switched back to main document")
            except:
                # If switching back fails, just reload the original URL
                try:
                    self.driver.get(current_url)
                    logger.debug("Reloaded original URL")
                    time.sleep(2)
                except:
                    pass
                
            # Return True if we found any new streams
            return len(self.stream_links) > initial_stream_count
            
        except Exception as e:
            logger.debug(f"Error in switch_to_iframe_and_extract: {str(e)}")
            # Try to switch back to the main document
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def extract_with_browser(self, content_type, content_id, season=None, episode=None, dub=None):
        """
        Extract streams using browser automation
        
        Args:
            content_type: 'movie', 'tv', 'anime', or 'manga'
            content_id: ID of the content from IMDB or TMDB
            season: Season number (for TV shows)
            episode: Episode number (for TV shows and anime)
            dub: Dub option for anime (0 for sub, 1 for dub)
            
        Returns:
            Dictionary with stream links and subtitles
        """
        try:
            if not self.driver:
                self.start_browser()
                
            # Reset lists
            self.stream_links = []
            self.subtitles = []
            
            # First visit the main domain to set cookies and establish a valid session
            logger.info(f"Visiting main domain: {self.domain}")
            self.driver.get(self.domain)
            time.sleep(3)  # Wait for the main page to load
            
            # Check if we were redirected or blocked
            main_url = self.driver.current_url
            logger.debug(f"Main domain URL after navigation: {main_url}")
            
            if "new-tab-page" in main_url or "blocked" in main_url:
                logger.error(f"Access to main domain was redirected/blocked: {main_url}")
                # Take a screenshot of the blocked page
                try:
                    self.driver.save_screenshot('vidsrc_icu_blocked.png')
                    logger.debug("Saved screenshot of blocked page to vidsrc_icu_blocked.png")
                except:
                    pass
                return {'streams': [], 'subtitles': []}
            
            # Now try a direct API approach first
            try:
                logger.debug("Trying direct API approach via browser...")
                embed_url = self.generate_embed_url(content_type, content_id, season, episode)
                
                # Fetch the embed URL using browser's fetch API to avoid CORS issues
                fetch_script = f"""
                    return fetch("{embed_url}", {{
                        "headers": {{
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                            "Accept-Language": "en-US,en;q=0.9",
                            "Referer": "{self.domain}",
                            "User-Agent": "{self.user_agent}"
                        }},
                        "method": "GET"
                    }})
                    .then(response => response.text())
                    .catch(error => "ERROR: " + error.message);
                """
                
                fetch_result = self.driver.execute_script(fetch_script)
                if fetch_result and not fetch_result.startswith("ERROR:"):
                    logger.debug(f"Successfully fetched embed URL content via JavaScript fetch")
                    # Process the fetched content
                    if "<iframe" in fetch_result:
                        logger.debug("Found iframe in fetched content")
                        iframe_matches = re.findall(r'<iframe[^>]*src=["\'](.*?)["\']', fetch_result)
                        if iframe_matches:
                            for iframe_src in iframe_matches:
                                logger.debug(f"Found iframe src in fetched content: {iframe_src}")
                                if iframe_src.startswith("//"):
                                    iframe_src = "https:" + iframe_src
                                # Navigate to the iframe source
                                self.driver.get(iframe_src)
                                time.sleep(3)
                                # Extract from this page
                                self.extract_sources_from_page()
                                self.extract_subtitles_from_page()
                else:
                    logger.debug(f"JavaScript fetch failed: {fetch_result}")
            except Exception as e:
                logger.debug(f"Error in direct API approach via browser: {str(e)}")
            
            # If no streams found yet, try the normal navigation approach
            if not self.stream_links:
                # Generate the embed URL using our method
                embed_url = self.generate_embed_url(content_type, content_id, season, episode)
                    
                logger.info(f"Navigating to embed URL: {embed_url}")
                
                # Navigate to the embed URL
                self.driver.get(embed_url)
                
                # Wait for page to load
                time.sleep(5)
                
                # Save a screenshot for debugging if in debug mode
                try:
                    if logger.level <= logging.DEBUG:
                        self.driver.save_screenshot('vidsrc_icu_screenshot.png')
                        logger.debug("Saved debug screenshot to vidsrc_icu_screenshot.png")
                except Exception as e:
                    logger.debug(f"Failed to save screenshot: {str(e)}")
                
                # Document the page's URL after navigation (it might redirect)
                try:
                    final_url = self.driver.current_url
                    logger.debug(f"Final URL after navigation: {final_url}")
                    
                    # Save page source for debugging
                    if logger.level <= logging.DEBUG:
                        with open('vidsrc_icu_page_source.html', 'w', encoding='utf-8') as f:
                            f.write(self.driver.page_source)
                        logger.debug("Saved page source to vidsrc_icu_page_source.html")
                    
                    # Enhanced debugging - check if we're still on the expected domain
                    if 'vidsrc.icu' not in final_url and 'vidsrcme.vidsrc.icu' not in final_url:
                        logger.warning(f"Redirected away from vidsrc.icu to: {final_url}")
                except Exception as e:
                    logger.debug(f"Error capturing URL info: {str(e)}")
                    
                # Enhanced debugging - check for specific page elements
                try:
                    logger.debug("Looking for video elements on the page...")
                    video_elements = self.driver.find_elements(By.TAG_NAME, 'video')
                    logger.debug(f"Found {len(video_elements)} video elements")
                    
                    for i, video in enumerate(video_elements):
                        try:
                            src = video.get_attribute('src') or 'No src attribute'
                            style = video.get_attribute('style') or 'No style attribute'
                            classes = video.get_attribute('class') or 'No classes'
                            logger.debug(f"Video {i+1}: src={src}, class={classes}, style={style}")
                        except:
                            logger.debug(f"Could not get attributes for video {i+1}")
                    
                    logger.debug("Looking for iframe elements...")
                    iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                    logger.debug(f"Found {len(iframes)} iframes on page")
                    
                    for i, iframe in enumerate(iframes):
                        try:
                            src = iframe.get_attribute('src') or 'No src attribute'
                            id_attr = iframe.get_attribute('id') or 'No id attribute'
                            logger.debug(f"Iframe {i+1}: id={id_attr}, src={src}")
                        except:
                            logger.debug(f"Could not get attributes for iframe {i+1}")
                    
                    # Check for specific player id we found in the HTML
                    try:
                        video_iframe = self.driver.find_element(By.ID, 'videoIframe')
                        logger.debug(f"Found videoIframe with src: {video_iframe.get_attribute('src')}")
                    except:
                        logger.debug("No element with id 'videoIframe' found")
                    
                    # Check for specific player script elements
                    logger.debug("Looking for script elements that might initialize players...")
                    scripts = self.driver.find_elements(By.TAG_NAME, 'script')
                    logger.debug(f"Found {len(scripts)} script elements")
                    
                    for i, script in enumerate(scripts):
                        try:
                            src = script.get_attribute('src')
                            if src:
                                logger.debug(f"Script {i+1} src: {src}")
                        except:
                            pass
                            
                    # Execute some JS to check for player variables
                    logger.debug("Checking for player variables in JavaScript context...")
                    js_check = """
                        return {
                            hasJwplayer: typeof jwplayer !== 'undefined',
                            hasVideojs: typeof videojs !== 'undefined',
                            hasHls: typeof Hls !== 'undefined',
                            hasPlyr: typeof Plyr !== 'undefined',
                            videoElement: document.querySelector('video') !== null,
                            iframeCount: document.querySelectorAll('iframe').length,
                            bodyHTML: document.body.innerHTML.length
                        }
                    """
                    js_result = self.driver.execute_script(js_check)
                    logger.debug(f"JS environment check: {js_result}")
                    
                except Exception as e:
                    logger.debug(f"Error in enhanced debugging: {str(e)}")
                
                # Extract sources and subtitles
                self.extract_sources_from_page()
                self.extract_subtitles_from_page()
                
                # Rest of the function continues unchanged...
                
            # Log iframes on page
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                if iframes:
                    logger.debug(f"Found {len(iframes)} iframes on page")
                    for i in range(len(iframes)):
                        logger.debug(f"Attempting to extract from iframe {i}")
                        self.switch_to_iframe_and_extract(iframe_index=i)
                else:
                    logger.debug("No iframes found on the main page")
            except Exception as e:
                logger.debug(f"Error processing iframes: {str(e)}")
            
            # Try to check for server/source selection options
            try:
                # Common server selection elements
                server_selectors = [
                    '.server-item', '.server', '.source', '.server-btn', 
                    '[class*="server"]', '[class*="source"]', '[class*="provider"]',
                    '.host-select', '.host-item', '.mirror'
                ]
                
                for selector in server_selectors:
                    try:
                        server_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if server_elements:
                            logger.debug(f"Found {len(server_elements)} possible server selection elements with selector '{selector}'")
                            
                            # Try clicking on each server item to activate different sources
                            for i, element in enumerate(server_elements):
                                try:
                                    # Skip hidden elements
                                    if not element.is_displayed():
                                        continue
                                        
                                    try:
                                        server_name = element.text
                                        logger.debug(f"Attempting to click server: {server_name if server_name else f'Server {i+1}'}")
                                    except:
                                        pass
                                    
                                    # Try different clicking methods
                                    try:
                                        element.click()
                                    except:
                                        try:
                                            ActionChains(self.driver).move_to_element(element).click().perform()
                                        except:
                                            self.driver.execute_script("arguments[0].click();", element)
                                    
                                    # Wait for server switch
                                    time.sleep(3)
                                    
                                    # Extract sources and subtitles after each server switch
                                    self.extract_sources_from_page()
                                    self.extract_subtitles_from_page()
                                    
                                    # Check for new iframes that might have appeared
                                    try:
                                        new_iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                                        if len(new_iframes) > len(iframes):
                                            logger.debug(f"Found {len(new_iframes)} iframes after server switch (previously {len(iframes)})")
                                            for j in range(len(new_iframes)):
                                                self.switch_to_iframe_and_extract(iframe_index=j)
                                    except:
                                        pass
                                    
                                except Exception as e:
                                    logger.debug(f"Error clicking server element: {str(e)}")
                                    continue
                                
                    except Exception as e:
                        logger.debug(f"Error processing server selector '{selector}': {str(e)}")
                        continue
            except Exception as e:
                logger.debug(f"Error in server selection processing: {str(e)}")
            
            # If no streams found yet, do a general extraction
            if not self.stream_links:
                logger.debug("No streams found from iframes or server selection, trying general extraction...")
                # Extract sources and subtitles
                self.extract_sources_from_page()
                self.extract_subtitles_from_page()
            
            # If still no streams found, try to handle common player types
            if not self.stream_links:
                logger.debug("No streams found, trying common player types...")
                
                # Check for JW Player
                try:
                    jw_script = """
                        if (typeof jwplayer !== 'undefined') {
                            const players = jwplayer();
                            if (players && players.getPlaylist) {
                                const playlist = players.getPlaylist();
                                if (playlist && playlist.length > 0) {
                                    const sources = playlist[0].sources;
                                    return sources.map(s => s.file);
                                }
                            }
                        }
                        return [];
                    """
                    jw_sources = self.driver.execute_script(jw_script)
                    if jw_sources and isinstance(jw_sources, list):
                        for url in jw_sources:
                            if self.is_valid_stream_url(url):
                                self.stream_links.append(url)
                                logger.debug(f"Found JW Player source: {url}")
                except Exception as e:
                    logger.debug(f"Error checking JW Player: {str(e)}")
                    
                # Check for Video.js
                try:
                    videojs_script = """
                        if (typeof videojs !== 'undefined') {
                            const players = document.querySelectorAll('.video-js');
                            const results = [];
                            players.forEach(player => {
                                const id = player.id;
                                if (id && videojs(id)) {
                                    const vjsPlayer = videojs(id);
                                    if (vjsPlayer.src()) {
                                        results.push(vjsPlayer.src());
                                    }
                                }
                            });
                            return results;
                        }
                        return [];
                    """
                    vjs_sources = self.driver.execute_script(videojs_script)
                    if vjs_sources and isinstance(vjs_sources, list):
                        for url in vjs_sources:
                            if self.is_valid_stream_url(url):
                                self.stream_links.append(url)
                                logger.debug(f"Found Video.js source: {url}")
                except Exception as e:
                    logger.debug(f"Error checking Video.js: {str(e)}")
                    
                # Check for Plyr
                try:
                    plyr_script = """
                        if (typeof Plyr !== 'undefined') {
                            const players = document.querySelectorAll('.plyr');
                            const results = [];
                            players.forEach(player => {
                                const video = player.querySelector('video');
                                if (video && video.src) {
                                    results.push(video.src);
                                }
                            });
                            return results;
                        }
                        return [];
                    """
                    plyr_sources = self.driver.execute_script(plyr_script)
                    if plyr_sources and isinstance(plyr_sources, list):
                        for url in plyr_sources:
                            if self.is_valid_stream_url(url):
                                self.stream_links.append(url)
                                logger.debug(f"Found Plyr source: {url}")
                except Exception as e:
                    logger.debug(f"Error checking Plyr: {str(e)}")
            
            # Process the extracted links
            unique_links = list(set(self.stream_links))
            valid_links = []
            
            for link in unique_links:
                if self.is_valid_stream_url(link):
                    stream_type = 'hls' if '.m3u8' in link.lower() else 'mp4' if '.mp4' in link.lower() else 'unknown'
                    quality = 'auto'
                    
                    # Try to determine quality from URL or filename
                    quality_patterns = ['1080p', '720p', '480p', '360p']
                    for pattern in quality_patterns:
                        if pattern in link:
                            quality = pattern
                            break
                            
                    valid_links.append({
                        'type': stream_type,
                        'quality': quality,
                        'url': link
                    })
                    logger.debug(f"Processed valid link: {link}")
            
            # Process subtitles
            unique_subtitles = []
            seen_urls = set()
            
            for subtitle in self.subtitles:
                url = subtitle.get('src', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_subtitles.append(subtitle)
                    logger.debug(f"Added unique subtitle: {url}")
            
            logger.info(f"Browser extraction found {len(valid_links)} streams and {len(unique_subtitles)} subtitles")
            
            # If no streams found after all attempts, log additional information
            if not self.stream_links:
                logger.warning("No streams found after all extraction attempts")
                try:
                    # Save console logs
                    console_logs = self.driver.get_log('browser')
                    with open('vidsrc_icu_console_logs.txt', 'w') as f:
                        for log in console_logs:
                            f.write(f"{log}\n")
                    logger.debug("Saved browser console logs to vidsrc_icu_console_logs.txt")
                except:
                    pass
            
            return {
                'streams': valid_links,
                'subtitles': unique_subtitles
            }
            
        except Exception as e:
            logger.error(f"Error in extract_with_browser: {str(e)}")
            return {'streams': [], 'subtitles': []}
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self.driver = None
                except:
                    pass

    def get_stream_and_subtitle_links(self, content_type, content_id, season=None, episode=None, dub=None, force_browser=False):
        """
        Get stream links for the requested content
        
        Args:
            content_type: 'movie', 'tv', 'anime', or 'manga'
            content_id: ID of the content from IMDB or TMDB
            season: Season number (for TV shows)
            episode: Episode number (for TV shows and anime)
            dub: Dub option for anime (0 for sub, 1 for dub)
            force_browser: Force using browser even if API method might work
            
        Returns:
            Dictionary with stream links and subtitles
        """
        result = None
        
        # First try the API method unless browser is forced
        if not force_browser:
            logger.info("Trying direct API method...")
            api_result = self.extract_from_direct_api(content_type, content_id, season, episode, dub)
            
            if api_result and api_result.get('sources'):
                logger.info(f"Direct API method successful, found {len(api_result['sources'])} sources")
                
                # Convert the API result to the standard format
                streams = []
                for source in api_result['sources']:
                    streams.append({
                        'type': source.get('type', 'unknown'),
                        'quality': source.get('quality', 'auto'),
                        'url': source.get('file', '')
                    })
                    
                result = {
                    'streams': streams,
                    'subtitles': api_result.get('subtitles', [])
                }
        
        # If API method failed or was skipped, try browser method
        if not result or not result.get('streams'):
            logger.info("Using browser-based extraction...")
            result = self.extract_with_browser(content_type, content_id, season, episode, dub)
        
        return result

    def generate_embed_url(self, content_type, content_id, season=None, episode=None):
        """Generate the embed URL for the given content."""
        # Format the URL correctly based on content type and parameters
        season_episode = ""
        if content_type == "tv" and season is not None and episode is not None:
            season_episode = f"&s={season}&e={episode}"
        
        url = self.embed_url_format.format(
            content_type=content_type,
            id=content_id,
            season_episode=season_episode
        )
        
        self.logger.debug(f"Generated embed URL: {url}")
        return url

    @staticmethod
    def is_valid_stream_url(url):
        """Check if a URL is a valid stream URL"""
        if not url or not isinstance(url, str) or not url.startswith('http'):
            return False
            
        # Check for media file extensions and patterns
        media_patterns = [
            '.m3u8', '.mp4', '.ts', '.mpd', '.webm',
            '/manifest', '/playlist', '/stream', '/source',
            '/master.', '/hls/'
        ]
        
        has_media_pattern = any(pattern in url.lower() for pattern in media_patterns)
        
        # Skip known non-media URLs
        non_media_patterns = [
            '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', 
            'google', 'facebook', 'twitter', 'analytics'
        ]
        
        has_non_media_pattern = any(pattern in url.lower() for pattern in non_media_patterns)
        
        return has_media_pattern and not has_non_media_pattern

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Extract streams from vidsrc.icu')
    parser.add_argument('--id', help='TMDB ID or IMDB ID')
    parser.add_argument('--type', choices=['movie', 'tv'], default='movie', help='Content type (movie or tv)')
    parser.add_argument('--season', type=int, help='Season number (for TV shows)')
    parser.add_argument('--episode', type=int, help='Episode number (for TV shows)')
    parser.add_argument('--browser', action='store_true', help='Force browser-based extraction')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Default to Avengers: Endgame if no ID provided
    content_id = args.id or "299534"
    content_type = args.type
    
    # Initialize extractor
    extractor = VidsrcIcuExtractor(debug=args.debug)
    
    # Print banner
    print("\n======================================================================")
    if content_type == 'movie':
        print(f"   VidSrc.icu Stream Extractor - MOVIE ID: {content_id}")
    else:
        print(f"   VidSrc.icu Stream Extractor - TV SHOW ID: {content_id}, S{args.season}E{args.episode}")
    print("======================================================================\n")
    
    # Log what we're extracting
    if content_type == 'movie':
        logging.info(f"Extracting Movie ID: {content_id}")
    else:
        logging.info(f"Extracting TV Show ID: {content_id}, Season: {args.season}, Episode: {args.episode}")
    
    # Extract streams and subtitles
    result = extractor.get_stream_and_subtitle_links(
        content_type, 
        content_id, 
        args.season, 
        args.episode, 
        force_browser=args.browser
    )
    
    # Print results
    streams = result.get('streams', [])
    subtitles = result.get('subtitles', [])
    
    if streams:
        print("\nExtracted Stream Links:")
        for i, stream in enumerate(streams, 1):
            if isinstance(stream, dict):
                # Handle proper stream dictionary
                stream_type = stream.get('type', 'unknown')
                quality = stream.get('quality', 'auto')
                url = stream.get('url', '')
                
                if url:
                    print(f"  {i}. [{stream_type} - {quality}] {url}")
            elif isinstance(stream, str):
                # Handle direct URL strings
                print(f"  {i}. {stream}")
    else:
        print("\nNo stream links found.")
    
    if subtitles:
        print("\nExtracted Subtitle Tracks:")
        for i, sub in enumerate(subtitles, 1):
            if isinstance(sub, dict):
                # Handle subtitle dictionary
                kind = sub.get('kind', 'subtitle')
                label = sub.get('label', 'Unknown')
                language = sub.get('language', 'unknown')
                src = sub.get('src', '')
                
                if src:
                    print(f"  {i}. [{language}] {label} - {src}")
            elif isinstance(sub, str):
                # Handle direct URL strings
                print(f"  {i}. {sub}")
    else:
        print("\nNo subtitle tracks found.")

if __name__ == "__main__":
    main() 