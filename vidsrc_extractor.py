import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementNotInteractableException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
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

class StreamExtractor:
    def __init__(self, headless=False):
        self.driver = None
        self.headless = headless
        self.wait_time = 10  # Reduced wait time
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
        ]
        self.user_agent = random.choice(self.user_agents)
        self.stream_links = []
        self.subtitles = []

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
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-save-password-bubble')
            options.add_argument('--disable-translate')
            options.add_argument('--enable-javascript')
            options.add_argument(f'--user-agent={self.user_agent}')
            
            if self.headless:
                options.add_argument('--headless=new')
            
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
            
            # Add custom JavaScript to mask automation
            self.inject_stealth_js()
            
            logger.info("Browser started successfully with advanced configuration")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {str(e)}")
            raise

    def inject_stealth_js(self):
        """Inject JavaScript to mask automation with advanced fingerprinting evasion"""
        stealth_js = """
            // Overwrite the webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
                configurable: true
            });
            
            // Add fake plugins and mime types
            const makePluginArray = () => {
                const plugins = [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ];
                
                const pluginArray = plugins.map(plugin => {
                    const pluginObj = {};
                    pluginObj.name = plugin.name;
                    pluginObj.filename = plugin.filename;
                    pluginObj.description = '';
                    pluginObj.version = '';
                    pluginObj.length = 1;
                    return pluginObj;
                });
                
                pluginArray.item = idx => pluginArray[idx];
                pluginArray.namedItem = name => pluginArray.find(plugin => plugin.name === name);
                pluginArray.refresh = () => {};
                Object.setPrototypeOf(pluginArray, PluginArray.prototype);
                return pluginArray;
            };
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => makePluginArray(),
                configurable: true
            });
            
            // Add chrome properties
            window.chrome = {
                app: {
                    isInstalled: false,
                    InstallState: {
                        DISABLED: 'disabled',
                        INSTALLED: 'installed',
                        NOT_INSTALLED: 'not_installed'
                    },
                    RunningState: {
                        CANNOT_RUN: 'cannot_run',
                        READY_TO_RUN: 'ready_to_run',
                        RUNNING: 'running'
                    }
                },
                runtime: {
                    OnInstalledReason: {
                        CHROME_UPDATE: 'chrome_update',
                        INSTALL: 'install',
                        SHARED_MODULE_UPDATE: 'shared_module_update',
                        UPDATE: 'update'
                    },
                    OnRestartRequiredReason: {
                        APP_UPDATE: 'app_update',
                        OS_UPDATE: 'os_update',
                        PERIODIC: 'periodic'
                    },
                    PlatformArch: {
                        ARM: 'arm',
                        ARM64: 'arm64',
                        MIPS: 'mips',
                        MIPS64: 'mips64',
                        X86_32: 'x86-32',
                        X86_64: 'x86-64'
                    },
                    PlatformNaclArch: {
                        ARM: 'arm',
                        MIPS: 'mips',
                        MIPS64: 'mips64',
                        X86_32: 'x86-32',
                        X86_64: 'x86-64'
                    },
                    PlatformOs: {
                        ANDROID: 'android',
                        CROS: 'cros',
                        LINUX: 'linux',
                        MAC: 'mac',
                        OPENBSD: 'openbsd',
                        WIN: 'win'
                    },
                    RequestUpdateCheckStatus: {
                        NO_UPDATE: 'no_update',
                        THROTTLED: 'throttled',
                        UPDATE_AVAILABLE: 'update_available'
                    }
                }
            };
            
            // Add languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'es'],
                configurable: true
            });
            
            // Fix iframe detection
            HTMLIFrameElement.prototype.contentWindow.Object.defineProperty = Object.defineProperty;
        """
        try:
            self.driver.execute_script(stealth_js)
        except Exception as e:
            logger.debug(f"Error injecting stealth JS: {str(e)}")
            pass

    def simulate_human_behavior(self):
        """Simulate realistic human behavior to avoid detection"""
        try:
            # Random delays between actions
            time.sleep(random.uniform(1.0, 3.0))
            
            # Random mouse movements
            actions = ActionChains(self.driver)
            for _ in range(random.randint(2, 5)):
                x, y = random.randint(100, 800), random.randint(100, 600)
                actions.move_by_offset(x, y)
                actions.pause(random.uniform(0.1, 0.3))
            actions.perform()
            
            # Random scrolling
            scroll_amount = random.randint(300, 700)
            self.driver.execute_script(f"window.scrollTo(0, {scroll_amount});")
            time.sleep(random.uniform(0.5, 1.5))
            
            # Scroll back up slowly
            self.driver.execute_script("""
                const scrollToTop = () => {
                    const currentPos = window.pageYOffset;
                    if (currentPos > 0) {
                        window.scrollTo(0, currentPos - 10);
                        setTimeout(scrollToTop, 20);
                    }
                };
                scrollToTop();
            """)
            
            time.sleep(random.uniform(0.5, 1.0))
        except Exception as e:
            logger.debug(f"Error simulating human behavior: {str(e)}")
            pass

    def extract_from_network_logs(self):
        """Extract stream URLs from network logs"""
        try:
            # Get browser logs
            logs = self.driver.get_log('performance')
            
            # Process logs
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    
                    # Look for network responses
                    if log.get('method') == 'Network.responseReceived':
                        response = log.get('params', {}).get('response', {})
                        url = response.get('url', '')
                        
                        # Check for media URLs
                        if self.is_valid_url(url):
                            self.stream_links.append(url)
                            
                        # Check headers for additional URLs
                        headers = response.get('headers', {})
                        for header_value in headers.values():
                            if isinstance(header_value, str) and ('http://' in header_value or 'https://' in header_value):
                                potential_urls = re.findall(r'https?://[^\s<>"\']+', header_value)
                                for potential_url in potential_urls:
                                    if self.is_valid_url(potential_url):
                                        self.stream_links.append(potential_url)
                
                    # Look for WebSocket frames that might contain URLs
                    elif log.get('method') == 'Network.webSocketFrameReceived':
                        payload = log.get('params', {}).get('response', {}).get('payloadData', '')
                        if payload and isinstance(payload, str):
                            potential_urls = re.findall(r'https?://[^\s<>"\']+', payload)
                            for url in potential_urls:
                                if self.is_valid_url(url):
                                    self.stream_links.append(url)
                except:
                    continue
        except Exception as e:
            logger.debug(f"Error extracting from network logs: {str(e)}")

    def extract_from_page_variables(self):
        """Extract stream URLs from JavaScript variables in the page"""
        try:
            # Advanced JavaScript to extract URLs from various page variables
            js_extract = """
                function findStreams() {
                    const results = [];
                    
                    // Helper to recursively search for URLs in objects
                    function searchObject(obj, depth = 0) {
                        if (depth > 10) return; // Prevent infinite recursion
                        
                        if (obj === null || obj === undefined) return;
                        if (typeof obj === 'string') {
                            if (obj.match(/^https?:\\/\\/.*\\.(m3u8|mp4)/i) || 
                                obj.match(/^https?:\\/\\/.*\\/(stream|manifest|proxy)/i)) {
                                results.push(obj);
                            }
                            return;
                        }
                        
                        if (typeof obj !== 'object') return;
                        
                        for (const key in obj) {
                            try {
                                searchObject(obj[key], depth + 1);
                            } catch (e) {
                                // Ignore errors
                            }
                        }
                    }
                    
                    // Search in common variable names
                    const varNames = ['player', 'config', 'source', 'sources', 'stream', 'video', 'media',
                                     '_player', 'playerConfig', 'hlsUrl', 'videoSrc', 'url', 'streamUrl',
                                     'streams', 'hlsConfig', 'videoConfig', 'playerInstance'];
                    
                    for (const name of varNames) {
                        try {
                            if (window[name]) searchObject(window[name]);
                        } catch (e) {
                            // Ignore errors
                        }
                    }
                    
                    // Search in video elements' data attributes
                    document.querySelectorAll('video').forEach(video => {
                        for (const attr of video.attributes) {
                            if (attr.name.startsWith('data-')) {
                                try {
                                    const value = video.getAttribute(attr.name);
                                    if (value && value.match(/^https?:/)) {
                                        results.push(value);
                                    } else if (value && (value.startsWith('{') || value.startsWith('['))) {
                                        try {
                                            const parsed = JSON.parse(value);
                                            searchObject(parsed);
                                        } catch (e) {
                                            // Not valid JSON
                                        }
                                    }
                                } catch (e) {
                                    // Ignore errors
                                }
                            }
                        }
                    });
                    
                    // Search all script tags for inline JSON with URLs
                    document.querySelectorAll('script:not([src])').forEach(script => {
                        const content = script.textContent;
                        if (!content) return;
                        
                        // Look for JSON objects in the script
                        const jsonMatches = content.match(/[{\\[].*?[}\\]]/g);
                        if (jsonMatches) {
                            for (const match of jsonMatches) {
                                try {
                                    const parsed = JSON.parse(match);
                                    searchObject(parsed);
                                } catch (e) {
                                    // Not valid JSON
                                }
                            }
                        }
                        
                        // Look for direct URL assignments
                        const urlMatches = content.match(/(['"])https?:\\/\\/[^'"\s]+\\1/g);
                        if (urlMatches) {
                            for (const match of urlMatches) {
                                // Remove the quotes
                                const url = match.slice(1, -1);
                                if (url.match(/\\.(m3u8|mp4)/i) || url.match(/\\/(stream|manifest|proxy)/i)) {
                                    results.push(url);
                                }
                            }
                        }
                    });
                    
                    return [...new Set(results)]; // Return unique URLs
                }
                return findStreams();
            """
            
            # Execute in main frame
            urls = self.driver.execute_script(js_extract)
            if urls and isinstance(urls, list):
                self.stream_links.extend(urls)
            
            # Try to execute in all iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for i, iframe in enumerate(iframes):
                try:
                    self.driver.switch_to.frame(iframe)
                    urls = self.driver.execute_script(js_extract)
                    if urls and isinstance(urls, list):
                        self.stream_links.extend(urls)
                    self.driver.switch_to.default_content()
                except:
                    self.driver.switch_to.default_content()
                    continue
                    
        except Exception as e:
            logger.debug(f"Error extracting from page variables: {str(e)}")
            self.driver.switch_to.default_content()

    def extract_from_xhr_parameters(self):
        """Try to extract URL parameters from XHR requests that might contain encoded URLs"""
        try:
            # JavaScript to intercept fetch and XHR requests
            intercept_js = """
                // Store original methods
                const originalFetch = window.fetch;
                const originalXhrOpen = XMLHttpRequest.prototype.open;
                const originalXhrSend = XMLHttpRequest.prototype.send;
                
                // URLs collected
                window._interceptedUrls = window._interceptedUrls || [];
                
                // Intercept fetch
                window.fetch = function(...args) {
                    const url = args[0];
                    if (typeof url === 'string') {
                        window._interceptedUrls.push(url);
                    }
                    return originalFetch.apply(this, args);
                };
                
                // Intercept XHR
                XMLHttpRequest.prototype.open = function(method, url, ...rest) {
                    this._url = url;
                    return originalXhrOpen.apply(this, [method, url, ...rest]);
                };
                
                XMLHttpRequest.prototype.send = function(body) {
                    if (this._url) {
                        window._interceptedUrls.push(this._url);
                    }
                    return originalXhrSend.apply(this, [body]);
                };
            """
            
            # Inject the interception code
            self.driver.execute_script(intercept_js)
            
            # Wait for some requests to happen
            time.sleep(5)
            
            # Get the collected URLs
            intercepted_urls = self.driver.execute_script("return window._interceptedUrls || [];")
            
            # Process intercepted URLs
            for url in intercepted_urls:
                if isinstance(url, str):
                    # Check the URL itself
                    if self.is_valid_url(url):
                        self.stream_links.append(url)
                    
                    # Check for URL parameters that might be encoded
                    parsed = urlparse(url)
                    params = parse_qs(parsed.query)
                    
                    # Check common parameter names that might contain URLs
                    url_param_names = ['url', 'src', 'source', 'video', 'stream', 'file', 'link', 'path', 'u', 'v']
                    for param_name in url_param_names:
                        if param_name in params:
                            for param_value in params[param_name]:
                                # Try direct URL
                                if self.is_valid_url(param_value):
                                    self.stream_links.append(param_value)
                                
                                # Try URL decoding
                                try:
                                    decoded = unquote(param_value)
                                    if self.is_valid_url(decoded):
                                        self.stream_links.append(decoded)
                                except:
                                    pass
                                
                                # Try base64 decoding
                                try:
                                    decoded = decode_base64_url(param_value)
                                    if decoded and self.is_valid_url(decoded):
                                        self.stream_links.append(decoded)
                                except:
                                    pass
        except Exception as e:
            logger.debug(f"Error extracting from XHR parameters: {str(e)}")

    def attempt_server_switch(self, movie_id):
        """Try accessing different servers if available"""
        try:
            # Look for server selection options
            server_selectors = [
                ".server-option", ".server-item", ".server-switch", "[data-server]",
                "a[href*='server']", "button[data-server]", "button[data-source]",
                ".button[data-link]", "[class*='server']", "[class*='source']"
            ]
            
            for selector in server_selectors:
                server_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                if server_elements:
                    logger.info(f"Found {len(server_elements)} server options")
                    
                    # Try clicking each server option
                    for i, element in enumerate(server_elements):
                        try:
                            # Record current URL
                            current_url = self.driver.current_url
                            
                            # Click the server option
                            self.driver.execute_script("arguments[0].click();", element)
                            
                            # Wait for content to load
                            time.sleep(3)
                            
                            # Check if URL changed
                            if self.driver.current_url != current_url:
                                # Try to extract from the new server
                                self.extract_sources_from_page()
                            
                            # If we found any links, no need to continue
                            if self.stream_links:
                                break
                                
                        except Exception as e:
                            logger.debug(f"Error switching to server {i}: {str(e)}")
                            continue
                    
                    # If we found links by server switching, return them
                    if self.stream_links:
                        return True
            
            return False
        except Exception as e:
            logger.debug(f"Error attempting server switch: {str(e)}")
            return False

    def extract_sources_from_page(self):
        """Extract sources from the current page using multiple methods"""
        try:
            # First, try to find and click any play buttons to activate media
            play_selectors = [
                '.jw-icon-display', '.plyr__control--overlaid', '.play-button', 
                '[class*="play"]', '[id*="play"]', '.vjs-big-play-button',
                '.ytp-large-play-button', '.mejs__overlay-button', '[aria-label="Play"]',
                'button', '.btn', 'a[href="#play"]', 'i[class*="play"]'
            ]
            
            for selector in play_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        try:
                            # Skip hidden or non-visible elements
                            if not element.is_displayed():
                                continue
                                
                            # Scroll to the element
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(1)
                            
                            # Try multiple ways to click
                            try:
                                element.click()
                            except:
                                try:
                                    ActionChains(self.driver).move_to_element(element).click().perform()
                                except:
                                    self.driver.execute_script("arguments[0].click();", element)
                                    
                            time.sleep(3)  # Wait for click effects
                        except:
                            continue
                except:
                    continue
            
            # Try to extract URLs from JavaScript variables
            self.extract_from_page_variables()
            
            # Try to extract from network logs
            self.extract_from_network_logs()
            
            # Try to extract from XHR parameters
            self.extract_from_xhr_parameters()
            
            # Extract from page source
            page_source = self.driver.page_source
            
            # Look for direct video and source elements
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Look for video elements
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
            
            # Look for iframe src values that might contain video players
            for iframe in soup.find_all('iframe'):
                if iframe.get('src') and iframe['src'].startswith('http'):
                    iframe_src = iframe['src']
                    # Check if it looks like a video embed
                    if 'embed' in iframe_src or 'player' in iframe_src or 'video' in iframe_src:
                        # Try to access the iframe directly
                        try:
                            self.driver.get(iframe_src)
                            time.sleep(3)
                            self.extract_sources_from_page()  # Recursive call to extract from iframe
                            self.driver.back()  # Go back to original page
                        except:
                            pass
            
            # Look for various URL patterns in the page source
            patterns = [
                r'https?://[^\s<>"\']+?\.m3u8[^\s<>"\']*',
                r'https?://[^\s<>"\']+?\.mp4[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/stream[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/manifest[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/master\.txt[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/playlist\.m3u8[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/proxy[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/hls[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/dash[^\s<>"\']*'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_source)
                for match in matches:
                    self.stream_links.append(match)
            
            # Try to find any potential base64 encoded URLs
            encoded_patterns = [
                r'"([A-Za-z0-9+/\-_]+={0,2})"',
                r'\'([A-Za-z0-9+/\-_]+={0,2})\'',
                r'=([A-Za-z0-9+/\-_]+={0,2})',
                r'/([A-Za-z0-9+/\-_]{30,}={0,2})'
            ]
            
            for pattern in encoded_patterns:
                matches = re.findall(pattern, page_source)
                for encoded in matches:
                    # Only try to decode strings that are likely to be base64 (at least 20 chars)
                    if len(encoded) >= 20:
                        decoded = decode_base64_url(encoded)
                        if decoded and decoded.startswith('http'):
                            self.stream_links.append(decoded)
        
        except Exception as e:
            logger.debug(f"Error extracting sources from page: {str(e)}")

    def extract_subtitles_from_page(self):
        """Extract subtitle tracks from the current page"""
        try:
            # First check if we need to click a "CC" button or other subtitle toggle
            cc_selectors = [
                '[aria-label="Subtitles"]', '[aria-label="Captions"]', '.vjs-subs-caps-button',
                '.ytp-subtitles-button', '.jw-icon-cc', '.mejs__captions-button',
                '[class*="subtitle"]', '[class*="caption"]', 'button:contains("CC")',
                'button:contains("Subtitles")', '.plyr__control[data-plyr="captions"]'
            ]
            
            for selector in cc_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        try:
                            if element.is_displayed():
                                # Try to click the CC button to make subtitles available
                                self.driver.execute_script("arguments[0].click();", element)
                                time.sleep(1)
                        except:
                            continue
                except:
                    continue
            
            # Check for subtitles in video elements
            js_extract_subtitles = """
                function findSubtitles() {
                    const results = [];
                    
                    // Look for subtitle tracks in video elements
                    document.querySelectorAll('video').forEach(video => {
                        if (video.textTracks && video.textTracks.length > 0) {
                            for (let i = 0; i < video.textTracks.length; i++) {
                                const track = video.textTracks[i];
                                results.push({
                                    kind: track.kind,
                                    label: track.label,
                                    language: track.language,
                                    mode: track.mode,
                                    id: track.id
                                });
                            }
                        }
                    });
                    
                    // Look for track elements
                    document.querySelectorAll('track').forEach(track => {
                        results.push({
                            kind: track.kind,
                            label: track.label,
                            language: track.srclang,
                            src: track.src,
                            default: track.default
                        });
                    });
                    
                    // Look for player configurations that might contain subtitle info
                    const playerConfigs = [];
                    try {
                        // Common player config variables
                        const configVars = ['playerConfig', 'jwConfig', 'player.options', 'videoConfig', 'hlsjsConfig'];
                        for (const varName of configVars) {
                            try {
                                const config = eval(varName);
                                if (config) playerConfigs.push(config);
                            } catch (e) {}
                        }
                        
                        // Try to find player instances
                        if (window.jwplayer) {
                            const players = window.jwplayer();
                            if (players && players.getConfig) {
                                playerConfigs.push(players.getConfig());
                            }
                        }
                        
                        // Extract subtitle info from configs
                        for (const config of playerConfigs) {
                            if (config.tracks) {
                                config.tracks.forEach(track => {
                                    if (track.kind === 'captions' || track.kind === 'subtitles') {
                                        results.push(track);
                                    }
                                });
                            }
                        }
                    } catch (e) {}
                    
                    return results;
                }
                return findSubtitles();
            """
            
            # Execute in main frame
            subtitle_elements = self.driver.execute_script(js_extract_subtitles)
            if subtitle_elements and isinstance(subtitle_elements, list):
                for subtitle in subtitle_elements:
                    if subtitle and isinstance(subtitle, dict):
                        if 'src' in subtitle and subtitle['src'].startswith('http'):
                            self.subtitles.append(subtitle)
            
            # Try to execute in all iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for i, iframe in enumerate(iframes):
                try:
                    self.driver.switch_to.frame(iframe)
                    subtitle_elements = self.driver.execute_script(js_extract_subtitles)
                    if subtitle_elements and isinstance(subtitle_elements, list):
                        for subtitle in subtitle_elements:
                            if subtitle and isinstance(subtitle, dict):
                                if 'src' in subtitle and subtitle['src'].startswith('http'):
                                    self.subtitles.append(subtitle)
                    self.driver.switch_to.default_content()
                except:
                    self.driver.switch_to.default_content()
                    continue
            
            # Look for subtitle URLs in the page source
            page_source = self.driver.page_source
            
            # Find subtitle URLs using regex
            subtitle_patterns = [
                r'https?://[^\s<>"\']+?\.vtt[^\s<>"\']*',
                r'https?://[^\s<>"\']+?\.srt[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/subtitles/[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/captions/[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/subtitle[^\s<>"\']*',
                r'https?://[^\s<>"\']+?/caption[^\s<>"\']*',
                r'https?://[^\s<>"\']+?\.ttml[^\s<>"\']*',
                r'https?://[^\s<>"\']+?\.dfxp[^\s<>"\']*',
                r'https?://[^\s<>"\']+?\.xml[^\s<>"\']*caption[^\s<>"\']*',
                r'https?://[^\s<>"\']+?\.ass[^\s<>"\']*',
                r'https?://[^\s<>"\']+?\.ssa[^\s<>"\']*',
                r'https?://[^\s<>"\']+?\.sub[^\s<>"\']*'
            ]
            
            for pattern in subtitle_patterns:
                matches = re.findall(pattern, page_source)
                for match in matches:
                    self.subtitles.append({
                        'kind': 'subtitles',
                        'src': match,
                        'label': 'Auto-detected',
                        'language': 'auto'
                    })
            
            # Check for JSON data that might contain subtitle information
            json_pattern = r'({[^}]*?"tracks"[^}]*?})'
            json_matches = re.findall(json_pattern, page_source)
            
            for json_str in json_matches:
                try:
                    # Try to fix incomplete JSON 
                    if not json_str.startswith('{'):
                        json_str = '{' + json_str
                    if not json_str.endswith('}'):
                        json_str = json_str + '}'
                    
                    # Load and parse JSON
                    data = json.loads(json_str)
                    if 'tracks' in data and isinstance(data['tracks'], list):
                        for track in data['tracks']:
                            if isinstance(track, dict) and 'file' in track and track['file'].startswith('http'):
                                if 'kind' in track and track['kind'] in ['captions', 'subtitles']:
                                    self.subtitles.append({
                                        'kind': track['kind'],
                                        'src': track['file'],
                                        'label': track.get('label', 'Unknown'),
                                        'language': track.get('language', 'unknown')
                                    })
                except:
                    continue
            
            # Try looking for JSON in script tags
            soup = BeautifulSoup(page_source, 'html.parser')
            for script in soup.find_all('script'):
                script_text = script.string
                if script_text:
                    # Look for subtitle tracks in JSON
                    try:
                        # Look for objects with "tracks" properties
                        track_matches = re.findall(r'tracks\s*:\s*(\[[^\]]+\])', script_text)
                        
                        for track_match in track_matches:
                            # Try to fix JSON syntax (add proper quotes, etc.)
                            track_match = track_match.replace("'", '"')
                            
                            # Try to parse as JSON
                            try:
                                tracks = json.loads(track_match)
                                for track in tracks:
                                    if isinstance(track, dict) and ('file' in track or 'src' in track):
                                        track_url = track.get('file', track.get('src', ''))
                                        if track_url and track_url.startswith('http'):
                                            if 'kind' in track and track['kind'] in ['captions', 'subtitles']:
                                                self.subtitles.append({
                                                    'kind': track['kind'],
                                                    'src': track_url,
                                                    'label': track.get('label', 'Unknown'),
                                                    'language': track.get('language', 'unknown')
                                                })
                            except:
                                pass
                    except:
                        pass
                    
        except Exception as e:
            logger.debug(f"Error extracting subtitles from page: {str(e)}")
            self.driver.switch_to.default_content()

    def extract_subtitles_from_network(self):
        """Extract subtitles from network traffic"""
        try:
            # Get browser logs
            logs = self.driver.get_log('performance')
            
            # Process logs
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    
                    # Look for network responses that might be subtitles
                    if log.get('method') == 'Network.responseReceived':
                        response = log.get('params', {}).get('response', {})
                        url = response.get('url', '')
                        content_type = response.get('headers', {}).get('Content-Type', '').lower()
                        
                        # Check for subtitle content types or URLs
                        is_subtitle = False
                        
                        if any(ext in url.lower() for ext in ['.vtt', '.srt', '.ttml', '.dfxp', '.sub', '/subtitles/', '/captions/']):
                            is_subtitle = True
                        
                        if 'text/vtt' in content_type or 'application/x-subrip' in content_type:
                            is_subtitle = True
                            
                        if is_subtitle:
                            language = 'unknown'
                            label = 'Auto-detected'
                            
                            # Try to extract language from URL
                            lang_match = re.search(r'[/&?](?:lang|language)=([a-zA-Z-]+)', url)
                            if lang_match:
                                language = lang_match.group(1)
                                
                            # Try to get language from URL path
                            if 'unknown' in language:
                                lang_codes = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh', 'ar']
                                for code in lang_codes:
                                    if f'/{code}/' in url.lower() or f'.{code}.' in url.lower() or f'_{code}.' in url.lower():
                                        language = code
                                        break
                            
                            # Add to subtitles list
                            self.subtitles.append({
                                'kind': 'subtitles',
                                'src': url,
                                'label': f'Language: {language.upper()}',
                                'language': language
                            })
                            
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error extracting subtitles from network: {str(e)}")

    def extract_all_subtitles(self):
        """Extract subtitles using all available methods"""
        self.subtitles = []  # Reset subtitles list
        
        # Extract from page
        self.extract_subtitles_from_page()
        
        # Extract from network traffic
        self.extract_subtitles_from_network()
        
        # Extract from video players
        self.extract_subtitles_from_video_players()
        
        # Remove duplicates
        unique_subtitles = []
        seen_urls = set()
        
        for subtitle in self.subtitles:
            if not subtitle.get('src') or subtitle['src'] in seen_urls:
                continue
                
            seen_urls.add(subtitle['src'])
            unique_subtitles.append(subtitle)
            
        self.subtitles = unique_subtitles
        
        # Try to fetch and validate each subtitle
        validated_subtitles = []
        
        for subtitle in self.subtitles:
            try:
                url = subtitle['src']
                
                # Set up headers for the request
                headers = {
                    'User-Agent': self.user_agent,
                    'Accept': '*/*',
                    'Referer': self.driver.current_url,
                    'Origin': urlparse(self.driver.current_url).netloc
                }
                
                # Try to fetch the subtitle file
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    # Check if content looks like a subtitle file
                    content = response.text.strip().lower()
                    is_valid = False
                    
                    # Check for VTT format
                    if content.startswith('webvtt') or '-->':
                        is_valid = True
                        subtitle['format'] = 'vtt'
                    
                    # Check for SRT format
                    elif re.search(r'^\d+\s+\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', content):
                        is_valid = True
                        subtitle['format'] = 'srt'
                    
                    # Add content for smaller subtitle files
                    if is_valid and len(content) < 50000:  # Only include content if it's not too large
                        subtitle['content'] = response.text
                    
                    if is_valid:
                        validated_subtitles.append(subtitle)
            except Exception as e:
                logger.debug(f"Error validating subtitle {subtitle.get('src')}: {str(e)}")
                
        # Return validated subtitles
        return validated_subtitles

    def extract_subtitles_from_video_players(self):
        """Extract subtitles specifically from video players"""
        try:
            # Advanced JavaScript to extract subtitles from various player types
            js_extract = """
                function findVideoPlayerSubtitles() {
                    const results = [];
                    
                    // JW Player
                    if (window.jwplayer) {
                        try {
                            const players = document.querySelectorAll('[id^="jwplayer"][id$="div"]');
                            for (const playerEl of players) {
                                const id = playerEl.id.replace('_div', '');
                                const player = window.jwplayer(id);
                                if (player && player.getConfig) {
                                    const config = player.getConfig();
                                    if (config && config.tracks) {
                                        for (const track of config.tracks) {
                                            if ((track.kind === 'captions' || track.kind === 'subtitles') && track.file) {
                                                results.push({
                                                    kind: track.kind,
                                                    src: track.file,
                                                    label: track.label || 'Unknown',
                                                    language: track.language || 'unknown'
                                                });
                                            }
                                        }
                                    }
                                }
                            }
                        } catch (e) {}
                    }
                    
                    // HTML5 Video
                    document.querySelectorAll('video').forEach(video => {
                        // Check for track elements
                        const tracks = video.querySelectorAll('track');
                        for (const track of tracks) {
                            if (track.kind === 'subtitles' || track.kind === 'captions') {
                                results.push({
                                    kind: track.kind,
                                    src: track.src,
                                    label: track.label || 'Unknown',
                                    language: track.srclang || 'unknown',
                                    default: track.default
                                });
                            }
                        }
                        
                        // Check textTracks API
                        if (video.textTracks) {
                            for (let i = 0; i < video.textTracks.length; i++) {
                                const track = video.textTracks[i];
                                if (track.kind === 'subtitles' || track.kind === 'captions') {
                                    // For some players, we might be able to get the URL
                                    let url = '';
                                    if (track.track && track.track.src) {
                                        url = track.track.src;
                                    } else if (track.cues && track.cues.length > 0 && track.cues[0].text) {
                                        // Some players dynamically load cues, we can't get URL but we can get data
                                        url = 'dynamic:' + i; // Mark as dynamic
                                    }
                                    
                                    if (url) {
                                        results.push({
                                            kind: track.kind,
                                            src: url,
                                            label: track.label || 'Unknown',
                                            language: track.language || 'unknown',
                                            mode: track.mode
                                        });
                                    }
                                }
                            }
                        }
                    });
                    
                    // Plyr player
                    if (window.Plyr) {
                        try {
                            document.querySelectorAll('.plyr').forEach(playerEl => {
                                const instance = playerEl._plyr;
                                if (instance && instance.config) {
                                    const captions = instance.config.captions;
                                    if (captions && captions.active && captions.src) {
                                        results.push({
                                            kind: 'captions',
                                            src: captions.src,
                                            label: captions.language || 'Unknown',
                                            language: captions.language || 'unknown'
                                        });
                                    }
                                }
                            });
                        } catch (e) {}
                    }
                    
                    // Videojs
                    if (window.videojs) {
                        try {
                            document.querySelectorAll('.video-js').forEach(playerEl => {
                                const player = videojs.getPlayer(playerEl);
                                if (player && player.textTracks) {
                                    const tracks = player.textTracks();
                                    for (let i = 0; i < tracks.length; i++) {
                                        const track = tracks[i];
                                        if (track.kind === 'subtitles' || track.kind === 'captions') {
                                            // For videojs we might have remote or local tracks
                                            let url = '';
                                            if (track.src) {
                                                url = track.src;
                                            }
                                            
                                            if (url) {
                                                results.push({
                                                    kind: track.kind,
                                                    src: url,
                                                    label: track.label || 'Unknown',
                                                    language: track.language || 'unknown'
                                                });
                                            }
                                        }
                                    }
                                }
                            });
                        } catch (e) {}
                    }
                    
                    return results;
                }
                return findVideoPlayerSubtitles();
            """
            
            # Execute in main frame
            extracted_subtitles = self.driver.execute_script(js_extract)
            if extracted_subtitles and isinstance(extracted_subtitles, list):
                for subtitle in extracted_subtitles:
                    if subtitle and isinstance(subtitle, dict):
                        if 'src' in subtitle and subtitle['src'].startswith('http'):
                            self.subtitles.append(subtitle)
            
            # Try to execute in all iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for i, iframe in enumerate(iframes):
                try:
                    self.driver.switch_to.frame(iframe)
                    extracted_subtitles = self.driver.execute_script(js_extract)
                    if extracted_subtitles and isinstance(extracted_subtitles, list):
                        for subtitle in extracted_subtitles:
                            if subtitle and isinstance(subtitle, dict):
                                if 'src' in subtitle and subtitle['src'].startswith('http'):
                                    self.subtitles.append(subtitle)
                    self.driver.switch_to.default_content()
                except:
                    self.driver.switch_to.default_content()
                    continue
                    
        except Exception as e:
            logger.debug(f"Error extracting subtitles from video players: {str(e)}")
            self.driver.switch_to.default_content()

    def extract_subtitles_from_m3u8(self, m3u8_url):
        """Extract subtitle tracks directly from an M3U8 playlist"""
        try:
            logger.info(f"Trying to extract subtitles from M3U8: {m3u8_url}")
            
            # Use headers to avoid blocking
            headers = {
                'User-Agent': self.user_agent,
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://embed.su',
                'Referer': 'https://embed.su/',
            }
            
            # Get the M3U8 content
            response = requests.get(m3u8_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.debug(f"Failed to get M3U8 content: {response.status_code}")
                return []
            
            # Parse the M3U8 content
            m3u8_content = response.text
            
            # Check for subtitle tracks in the M3U8 content
            subtitle_tracks = []
            
            # Look for EXT-X-MEDIA entries for subtitles
            subtitle_entries = re.findall(r'#EXT-X-MEDIA:TYPE=SUBTITLES.*?\n', m3u8_content, re.DOTALL)
            
            for entry in subtitle_entries:
                # Extract subtitle URI, language, and name
                uri_match = re.search(r'URI="([^"]+)"', entry)
                language_match = re.search(r'LANGUAGE="([^"]+)"', entry)
                name_match = re.search(r'NAME="([^"]+)"', entry)
                
                if uri_match:
                    uri = uri_match.group(1)
                    language = language_match.group(1) if language_match else "unknown"
                    name = name_match.group(1) if name_match else f"Subtitle {language}"
                    
                    # Convert relative URI to absolute
                    if not uri.startswith('http'):
                        base_url = m3u8_url.rsplit('/', 1)[0]
                        uri = f"{base_url}/{uri}"
                    
                    subtitle_tracks.append({
                        'kind': 'subtitles',
                        'src': uri,
                        'label': name,
                        'language': language
                    })
                    
            # If no EXT-X-MEDIA entries, check for alternative streaming methods
            if not subtitle_tracks:
                # Get base URL for resolving relative paths
                base_url = m3u8_url.rsplit('/', 1)[0]
                
                # Check for subtitle segments
                subtitle_urls = re.findall(r'#EXTINF:.*?\n(.*?\.vtt|.*?\.srt)', m3u8_content, re.MULTILINE)
                
                for i, url in enumerate(subtitle_urls):
                    # Convert relative URL to absolute
                    if not url.startswith('http'):
                        url = f"{base_url}/{url}"
                    
                    subtitle_tracks.append({
                        'kind': 'subtitles',
                        'src': url,
                        'label': f"Subtitle Track {i+1}",
                        'language': "unknown"
                    })
                    
            # If we found subtitles in the M3U8, try to download one to determine language
            if subtitle_tracks and all(track['language'] == 'unknown' for track in subtitle_tracks):
                # Try to identify language from content of the first subtitle
                try:
                    sub_response = requests.get(subtitle_tracks[0]['src'], headers=headers, timeout=5)
                    if sub_response.status_code == 200:
                        content = sub_response.text.lower()
                        
                        # Check for language indicators in the content
                        if 'english' in content or 'eng' in content:
                            subtitle_tracks[0]['language'] = 'en'
                        elif 'español' in content or 'spanish' in content or 'spa' in content:
                            subtitle_tracks[0]['language'] = 'es'
                        elif 'français' in content or 'french' in content or 'fre' in content:
                            subtitle_tracks[0]['language'] = 'fr'
                        elif 'deutsch' in content or 'german' in content or 'ger' in content:
                            subtitle_tracks[0]['language'] = 'de'
                        
                        # Update the label
                        subtitle_tracks[0]['label'] = f"Subtitle [{subtitle_tracks[0]['language']}]"
                except:
                    pass
                
            return subtitle_tracks
                    
        except Exception as e:
            logger.debug(f"Error extracting subtitles from M3U8: {str(e)}")
            return []

    def fetch_subtitle_from_external_api(self, movie_id, language='en'):
        """Fetch subtitle data from external subtitle API services"""
        try:
            logger.info(f"Attempting to fetch subtitles from external API for movie ID: {movie_id}")
            
            # OpenSubtitles-like API approach (example only - would need actual API credentials)
            headers = {
                'User-Agent': self.user_agent,
                'Content-Type': 'application/json',
            }
            
            # Try to get IMDb ID if we have a numeric ID
            imdb_id = movie_id
            if movie_id.isdigit():
                imdb_id = f"tt{movie_id}"
            elif not movie_id.startswith('tt') and movie_id.isdigit():
                imdb_id = f"tt{movie_id}"
            
            # Use a subtitle search service
            subtitle_sources = [
                f"https://api.opensubtitles.com/api/v1/subtitles?imdb_id={imdb_id.replace('tt', '')}&languages={language}",
                f"https://rest.opensubtitles.org/search/imdbid-{imdb_id.replace('tt', '')}/sublanguageid-{language}"
            ]
            
            for source in subtitle_sources:
                try:
                    response = requests.get(source, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, dict) and 'data' in data and len(data['data']) > 0:
                            for item in data['data']:
                                if 'attributes' in item and 'files' in item['attributes']:
                                    for file in item['attributes']['files']:
                                        if 'file_id' in file:
                                            return {
                                                'kind': 'subtitles',
                                                'src': f"https://api.opensubtitles.com/api/v1/download/{file['file_id']}",
                                                'label': f"{language.upper()} Subtitle",
                                                'language': language,
                                                'source': 'OpenSubtitles'
                                            }
                        elif isinstance(data, list) and len(data) > 0:
                            # Old API format
                            for item in data:
                                if 'SubDownloadLink' in item:
                                    return {
                                        'kind': 'subtitles',
                                        'src': item['SubDownloadLink'],
                                        'label': item.get('MovieName', f"{language.upper()} Subtitle"),
                                        'language': language,
                                        'source': 'OpenSubtitles'
                                    }
                except Exception as e:
                    logger.debug(f"Error with subtitle source {source}: {str(e)}")
                    continue
            
            # Try alternative subtitle services (examples)
            alt_sources = [
                f"https://www.subtitlecat.com/index.php?search={imdb_id}",
                f"https://subscene.com/subtitles/searchbytitle?query={imdb_id}",
                f"https://yifysubtitles.org/movie-imdb/{imdb_id}"
            ]
            
            for url in alt_sources:
                try:
                    response = requests.get(url, headers={'User-Agent': self.user_agent}, timeout=10)
                    if response.status_code == 200:
                        # This would require HTML parsing to extract the actual subtitle links
                        # For demonstration purposes, we're not implementing the full extraction
                        # but this shows how you would approach it
                        pass
                except:
                    continue
                
            # If we couldn't find external subtitles, return a placeholder
            if language == 'en':
                return self.generate_placeholder_subtitle(movie_id)
                
            return None
        except Exception as e:
            logger.debug(f"Error fetching subtitles from external API: {str(e)}")
            return None

    def generate_placeholder_subtitle(self, movie_id):
        """Generate a placeholder subtitle file when no real subtitles are found"""
        try:
            # Create a simple WebVTT file with a placeholder message
            content = """WEBVTT

00:00:01.000 --> 00:00:06.000
No official subtitles available for this content.

00:00:07.000 --> 00:00:12.000
You may want to try external subtitle sources.

00:00:13.000 --> 00:00:18.000
Or use automatic subtitles in your player.
"""
            
            # Create a temporary file to store the subtitle
            import tempfile
            import os
            
            temp_dir = tempfile.gettempdir()
            subtitle_path = os.path.join(temp_dir, f"subtitle_{movie_id}.vtt")
            
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Return local file URL
            local_url = f"file:///{subtitle_path.replace('\\', '/')}"
            
            return {
                'kind': 'subtitles',
                'src': local_url,
                'label': 'Placeholder Subtitle',
                'language': 'en',
                'source': 'Generated',
                'local_path': subtitle_path
            }
        except Exception as e:
            logger.debug(f"Error generating placeholder subtitle: {str(e)}")
            return None

    def get_stream_and_subtitle_links(self, movie_id):
        """Get stream links and subtitles for a movie using advanced techniques"""
        self.stream_links = []  # Reset stream links
        self.subtitles = []  # Reset subtitles
        
        try:
            if not self.driver:
                self.start_browser()

            # Set dynamic movie base URL
            logger.info(f"Processing movie ID: {movie_id}")
            movie_ids = [movie_id]
            
            # Try alternative movie IDs if passed one fails
            if '.' in movie_id:  # If it's IMDb ID format (e.g., tt1234567)
                # Try both with and without tt prefix
                if movie_id.startswith('tt'):
                    # Add the version without tt
                    movie_ids.append(movie_id[2:])
                else:
                    # Add the version with tt
                    movie_ids.append('tt' + movie_id)
            
            for current_id in movie_ids:
                logger.info(f"Trying with ID: {current_id}")
                
                # First try direct API request
                logger.info("Trying direct API request...")
                api_url = f"https://embed.su/api/source/{current_id}"
                headers = {
                    'User-Agent': self.user_agent,
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Origin': 'https://embed.su',
                    'Referer': f'https://embed.su/embed/movie/{current_id}',
                    'Connection': 'keep-alive',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest'
                }
                
                try:
                    response = requests.post(api_url, headers=headers, data={'r': '', 'd': 'embed.su'}, timeout=10)
                    logger.info(f"API response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if 'data' in data and isinstance(data['data'], list):
                                for item in data['data']:
                                    if 'file' in item and item['file'].startswith('http'):
                                        self.stream_links.append(item['file'])
                                
                                # Check for subtitles in the API response
                                if 'tracks' in data and isinstance(data['tracks'], list):
                                    for track in data['tracks']:
                                        if (track.get('kind') == 'captions' or track.get('kind') == 'subtitles') and 'file' in track:
                                            self.subtitles.append({
                                                'kind': track.get('kind', 'subtitles'),
                                                'src': track['file'],
                                                'label': track.get('label', 'Unknown'),
                                                'language': track.get('language', 'unknown')
                                            })
                        except Exception as e:
                            logger.debug(f"Error parsing API response: {str(e)}")
                except Exception as e:
                    logger.error(f"API request failed: {str(e)}")

                # If API request failed or didn't return everything, try browser method
                if not self.stream_links or not self.subtitles:
                    logger.info("API method incomplete, trying browser method...")
                    
                    # Set up base headers for browser
                    self.driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
                        'headers': {
                            'Referer': 'https://embed.su/',
                            'Origin': 'https://embed.su',
                            'User-Agent': self.user_agent
                        }
                    })
                    
                    # Try different embed formats
                    embed_urls = [
                        f"https://embed.su/embed/movie/{current_id}",
                        f"https://embed.su/embed-4/{current_id}",
                        f"https://embed.su/embed/{current_id}"
                    ]
                    
                    for embed_url in embed_urls:
                        logger.info(f"Accessing URL: {embed_url}")
                        
                        self.driver.get(embed_url)
                        
                        # Wait for initial page load
                        time.sleep(5)
                        
                        # Try to click play to start loading media
                        self.extract_sources_from_page()
                        self.extract_subtitles_from_page()
                        
                        # If we found links, break out of the loop
                        if self.stream_links:
                            break
                    
                    # If still no links or subtitles, try server switching
                    if not self.stream_links or not self.subtitles:
                        logger.info("Trying to switch servers...")
                        self.attempt_server_switch(current_id)
                    
                    # Extract subtitles from network traffic
                    self.extract_subtitles_from_network()
                    
                    # Extract subtitles from video players
                    self.extract_subtitles_from_video_players()
                    
                    # If still no links or subtitles, check iframes recursively
                    if not self.stream_links or not self.subtitles:
                        logger.info("Checking iframes recursively...")
                        self.check_iframes_recursively()
                
                # If we found streams or subtitles with this ID, no need to try other IDs
                if self.stream_links or self.subtitles:
                    break

            # Try alternative data sources if no success yet
            if not self.stream_links:
                # Try other providers or formats
                logger.info("Trying alternative providers...")
                
                alt_providers = [
                    f"https://vidsrc.xyz/embed/movie?imdb={movie_id}",
                    f"https://2embed.to/embed/movie?imdb={movie_id}",
                    f"https://www.2embed.cc/embed/{movie_id}"
                ]
                
                for provider_url in alt_providers:
                    try:
                        self.driver.get(provider_url)
                        time.sleep(5)
                        
                        # Try to extract data from this provider
                        self.extract_sources_from_page()
                        self.extract_subtitles_from_page()
                        
                        # Extract from network
                        self.extract_from_network_logs()
                        
                        # If found streams, break out
                        if self.stream_links:
                            break
                    except Exception as e:
                        logger.debug(f"Error with alternative provider {provider_url}: {str(e)}")
                        continue

            # Remove duplicates and validate URLs
            unique_links = list(set(link for link in self.stream_links if self.is_valid_url(link)))
            
            # Try to validate each URL and get final URLs
            valid_links = []
            for link in unique_links:
                try:
                    headers = {
                        'User-Agent': self.user_agent,
                        'Accept': '*/*',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Origin': 'https://embed.su',
                        'Referer': 'https://embed.su/embed/movie/',
                        'Connection': 'keep-alive',
                        'Sec-Fetch-Dest': 'empty',
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'cross-site'
                    }
                    
                    # First try a HEAD request
                    response = requests.head(link, headers=headers, timeout=5, allow_redirects=True)
                    
                    # If it fails, try a GET request
                    if response.status_code != 200:
                        response = requests.get(link, headers=headers, timeout=5, stream=True)
                        response.close()  # Close the stream immediately to avoid downloading the whole file
                    
                    if response.status_code == 200:
                        final_url = response.url
                        valid_links.append(final_url)
                        logger.info(f"Validated URL: {final_url}")
                except Exception as e:
                    logger.debug(f"Error validating URL {link}: {str(e)}")
                    valid_links.append(link)  # Keep the link if we can't validate it

            # Get only playable stream URLs
            playable_links = self.get_final_playable_urls(valid_links)

            # Filter and validate subtitles
            valid_subtitles = []
            seen_subtitle_urls = set()
            
            for subtitle in self.subtitles:
                if not subtitle.get('src') or not isinstance(subtitle['src'], str):
                    continue
                    
                # Normalize URL
                url = subtitle['src'].strip()
                
                # Skip if we've already seen this URL
                if url in seen_subtitle_urls:
                    continue
                    
                seen_subtitle_urls.add(url)
                
                # Skip URLs that don't look like subtitle files unless they're from a reliable domain
                if not any(ext in url.lower() for ext in ['.vtt', '.srt', '.ttml', '.dfxp', '.sub', '.ass', '.ssa', '/subtitles/', '/captions/']):
                    # Only keep if from a known subtitle domain
                    if not any(domain in url.lower() for domain in ['api.', 'subtitles.', 'subs.', 'cc.']):
                        continue
                
                # Try to validate the URL
                try:
                    headers = {
                        'User-Agent': self.user_agent,
                        'Accept': '*/*',
                        'Referer': 'https://embed.su/',
                        'Origin': 'https://embed.su'
                    }
                    
                    response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
                    
                    if response.status_code == 200:
                        # Try to determine language if not specified
                        language = subtitle.get('language', 'unknown')
                        if language == 'unknown' or language == 'auto':
                            # Try to extract language from URL
                            for lang_code in ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh', 'ar']:
                                if f'/{lang_code}/' in url.lower() or f'.{lang_code}.' in url.lower() or f'_{lang_code}.' in url.lower():
                                    language = lang_code
                                    break
                        
                        # Add the validated subtitle
                        valid_subtitles.append({
                            'kind': subtitle.get('kind', 'subtitles'),
                            'src': response.url,  # Use the final URL after redirects
                            'label': subtitle.get('label', 'Unknown'),
                            'language': language
                        })
                except Exception as e:
                    logger.debug(f"Error validating subtitle URL {url}: {str(e)}")
                    # Keep the subtitle anyway
                    valid_subtitles.append(subtitle)

            # Make a final attempt to get subtitles from HLS streams if we have them but no subtitles
            if playable_links and not valid_subtitles:
                logger.info("Attempting to extract subtitles directly from M3U8 streams...")
                for link_info in playable_links:
                    # Try direct URL first (if available), then proxy URL
                    url = link_info.get('direct_url', link_info.get('url', ''))
                    if '.m3u8' in url:
                        m3u8_subtitles = self.extract_subtitles_from_m3u8(url)
                        if m3u8_subtitles:
                            valid_subtitles.extend(m3u8_subtitles)
                            logger.info(f"Found {len(m3u8_subtitles)} subtitle tracks in M3U8")
                            break  # Found subtitles, no need to check other streams
                
                # If no subtitles found in the first pass, try more advanced extraction
                if not valid_subtitles:
                    logger.info("Trying advanced subtitle extraction from variants...")
                    for link_info in playable_links:
                        url = link_info.get('direct_url', link_info.get('url', ''))
                        if '.m3u8' in url:
                            try:
                                headers = {
                                    'User-Agent': self.user_agent,
                                    'Accept': '*/*',
                                    'Referer': 'https://embed.su/'
                                }
                                
                                # Get the master playlist
                                response = requests.get(url, headers=headers, timeout=10)
                                
                                if response.status_code == 200:
                                    content = response.text
                                    
                                    # Look for variant streams
                                    variants = re.findall(r'#EXT-X-STREAM-INF:.*?\n(.*?\.m3u8)', content, re.MULTILINE)
                                    
                                    # Base URL for resolving relative paths
                                    base_url = url.rsplit('/', 1)[0]
                                    
                                    # Check each variant for subtitles
                                    for variant in variants:
                                        variant_url = variant if variant.startswith('http') else f"{base_url}/{variant}"
                                        m3u8_subtitles = self.extract_subtitles_from_m3u8(variant_url)
                                        if m3u8_subtitles:
                                            valid_subtitles.extend(m3u8_subtitles)
                                            logger.info(f"Found {len(m3u8_subtitles)} subtitle tracks in variant M3U8")
                                            break  # Found subtitles, no need to check other variants
                                    
                                    # If we found subtitles, no need to check other streams
                                    if valid_subtitles:
                                        break
                            except Exception as e:
                                logger.debug(f"Error checking variant streams: {str(e)}")
                                continue

            # Try to fetch subtitles from external sources if none found
            if not valid_subtitles:
                logger.info("No subtitles found in stream, trying external subtitle sources...")
                for lang in ['en', 'es', 'fr', 'de']:
                    external_subtitle = self.fetch_subtitle_from_external_api(movie_id, lang)
                    if external_subtitle:
                        valid_subtitles.append(external_subtitle)
                        logger.info(f"Found external subtitle: {external_subtitle['label']} ({external_subtitle.get('source', 'Unknown')})")
                        if lang == 'en':  # If we found English subtitles, stop searching
                            break

            # Print local paths for locally generated subtitle files
            for subtitle in valid_subtitles:
                if 'local_path' in subtitle:
                    logger.info(f"Generated subtitle file saved at: {subtitle['local_path']}")

            # Log results
            logger.info(f"Found {len(playable_links)} playable stream links")
            if playable_links:
                logger.info("Playable stream links:")
                for i, link_info in enumerate(playable_links):
                    logger.info(f"{i+1}. [{link_info['type']} - {link_info['quality']}] {link_info['url']}")
                    if 'decoded_info' in link_info:
                        logger.info(f"   Decoded: {link_info['decoded_info']}")
                    if 'direct_url' in link_info:
                        logger.info(f"   Direct URL: {link_info['direct_url']}")
            
            logger.info(f"Found {len(valid_subtitles)} subtitle tracks")
            if valid_subtitles:
                logger.info("Subtitle tracks:")
                for i, subtitle in enumerate(valid_subtitles):
                    logger.info(f"{i+1}. [{subtitle.get('language', 'unknown')}] {subtitle.get('label', 'Unknown')}: {subtitle.get('src', '')}")
            
            return {
                'streams': playable_links,
                'subtitles': valid_subtitles
            }

        except Exception as e:
            logger.error(f"Error extracting stream links and subtitles: {str(e)}")
            return {
                'streams': [],
                'subtitles': []
            }
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

    def check_iframes_recursively(self):
        """Check all iframes recursively for content"""
        def process_frame(max_depth=3, current_depth=0):
            if current_depth >= max_depth:
                return
                
            try:
                # Try to extract sources from the current iframe
                self.extract_sources_from_page()
                
                # Find all nested iframes
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                
                for i, iframe in enumerate(iframes):
                    try:
                        # Switch to iframe
                        self.driver.switch_to.frame(iframe)
                        
                        # Process this frame
                        process_frame(max_depth, current_depth + 1)
                        
                        # Switch back to parent
                        self.driver.switch_to.parent_frame()
                        
                    except Exception as e:
                        logger.debug(f"Error processing iframe {i} at depth {current_depth}: {str(e)}")
                        # Make sure we switch back to the parent
                        self.driver.switch_to.parent_frame()
                        continue
                        
            except Exception as e:
                logger.debug(f"Error in recursive iframe check at depth {current_depth}: {str(e)}")
                # Try to recover by switching back to default content
                self.driver.switch_to.default_content()
        
        try:
            # Start from the main page
            process_frame()
        except Exception as e:
            logger.debug(f"Error in recursive iframe check: {str(e)}")
            # Ensure we're back at the default content
            self.driver.switch_to.default_content()

    def convert_proxy_to_direct(self, proxy_url):
        """Convert a proxy URL to a direct URL by removing the proxy prefix"""
        try:
            if 'api/proxy/viper/' in proxy_url:
                # Remove the proxy prefix to get the direct URL
                direct_url = re.sub(r'https?://[^/]+/api/proxy/viper/', 'https://', proxy_url)
                return direct_url
            return proxy_url
        except:
            return proxy_url

    def get_final_playable_urls(self, valid_links):
        """Extract final playable URLs by filtering non-media URLs"""
        playable_links = []
        
        for link in valid_links:
            # Check if it's an .m3u8 URL
            if '.m3u8' in link.lower():
                link_info = {
                    'type': 'hls',
                    'quality': 'auto',
                    'url': link
                }
                
                # Check if it's a proxy URL and add direct URL if it is
                if 'api/proxy/viper/' in link:
                    direct_url = self.convert_proxy_to_direct(link)
                    link_info['direct_url'] = direct_url
                
                playable_links.append(link_info)
                
            # Check if it's an .mp4 URL and has quality info
            elif '.mp4' in link.lower():
                quality = 'Unknown'
                if '720p' in link or '720/' in link or '/720/' in link:
                    quality = '720p'
                elif '1080p' in link or '1080/' in link or '/1080/' in link:
                    quality = '1080p'
                elif '480p' in link or '480/' in link or '/480/' in link:
                    quality = '480p'
                elif '360p' in link or '360/' in link or '/360/' in link:
                    quality = '360p'
                
                link_info = {
                    'type': 'mp4',
                    'quality': quality,
                    'url': link
                }
                
                # Check if it's a proxy URL and add direct URL if it is
                if 'api/proxy/viper/' in link:
                    direct_url = self.convert_proxy_to_direct(link)
                    link_info['direct_url'] = direct_url
                
                playable_links.append(link_info)
                
            # Check for encoded URLs that might need further decoding
            elif '/proxy/' in link.lower() and not link.lower().endswith('.png'):
                # Try to extract the base64 encoded parts
                encoded_parts = re.findall(r'/([A-Za-z0-9+/\-_]{10,}={0,2})[./]', link)
                for encoded in encoded_parts:
                    try:
                        decoded = decode_base64_url(encoded)
                        if decoded and 'm3u8' in decoded.lower():
                            link_info = {
                                'type': 'hls',
                                'quality': 'auto',
                                'url': link,
                                'decoded_info': decoded
                            }
                            
                            # Check if it's a proxy URL and add direct URL if it is
                            if 'api/proxy/viper/' in link:
                                direct_url = self.convert_proxy_to_direct(link)
                                link_info['direct_url'] = direct_url
                            
                            playable_links.append(link_info)
                            break
                    except:
                        continue
                
                # If we didn't decode anything but it's likely a stream URL
                if not any('decoded_info' in item for item in playable_links if item['url'] == link):
                    link_info = {
                        'type': 'proxy',
                        'quality': 'auto',
                        'url': link
                    }
                    
                    # Check if it's a proxy URL and add direct URL if it is
                    if 'api/proxy/viper/' in link:
                        direct_url = self.convert_proxy_to_direct(link)
                        link_info['direct_url'] = direct_url
                    
                    playable_links.append(link_info)
        
        return playable_links

    @staticmethod
    def is_valid_url(url):
        """Check if a URL is valid and likely to be a stream URL"""
        try:
            if not url or not isinstance(url, str):
                return False
                
            result = urlparse(url)
            
            # Basic URL validation
            is_valid_structure = all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
            
            if not is_valid_structure:
                return False

            # Filter out static resource files that are not actual streams
            if '/static/' in url.lower() or url.lower().endswith('.js') or url.lower().endswith('.css'):
                return False
                
            # Check for common streaming URL patterns
            is_media_url = any(x in url.lower() for x in [
                '.m3u8', '.mp4', '.ts', '.mpd', '.webm', '.mp3', '.flv', '.f4v', 
                '/stream', '/manifest', '/proxy', '/hls', '/dash', '/playlist'
            ])
            
            # Make sure we're not catching image files
            if url.lower().endswith('.png') or url.lower().endswith('.jpg') or url.lower().endswith('.jpeg') or url.lower().endswith('.gif'):
                return False
            
            # Check for suspicious domains that are unlikely to be valid stream sources
            suspicious_domains = [
                'google.com', 'facebook.com', 'twitter.com', 'youtube.com', 
                'instagram.com', 'example.com', 'localhost'
            ]
            
            is_suspicious = any(domain in result.netloc.lower() for domain in suspicious_domains)
            
            return is_media_url and not is_suspicious
            
        except:
            return False

def main():
    # Example usage
    extractor = StreamExtractor(headless=False)
    try:
        # Use the original movie ID for testing
        movie_id = "310131"
        
        # Set a timeout for testing (in seconds)
        start_time = time.time()
        max_runtime = 60  # 1 minute max
        
        result = extractor.get_stream_and_subtitle_links(movie_id)
        
        print(f"\nExtraction completed in {time.time() - start_time:.2f} seconds")
        
        print("\nExtracted Stream Links:")
        for i, link_info in enumerate(result['streams']):
            print(f"{i+1}. [{link_info['type']} - {link_info['quality']}] {link_info['url']}")
            if 'decoded_info' in link_info:
                print(f"   Decoded: {link_info['decoded_info']}")
            if 'direct_url' in link_info:
                print(f"   Direct URL: {link_info['direct_url']}")
                
        print("\nExtracted Subtitle Tracks:")
        for i, subtitle in enumerate(result['subtitles']):
            print(f"{i+1}. [{subtitle.get('language', 'unknown')}] {subtitle.get('label', 'Unknown')}: {subtitle.get('src', '')}")
    except KeyboardInterrupt:
        print("\nExtraction stopped by user")
    finally:
        if extractor.driver:
            try:
                extractor.driver.quit()
            except:
                pass

if __name__ == "__main__":
    main() 