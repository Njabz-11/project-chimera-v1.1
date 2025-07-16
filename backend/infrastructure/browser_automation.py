"""
Browser Automation Infrastructure for Project Chimera
Provides Playwright-based web scraping and automation capabilities
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor
import json

try:
    from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright not available")


class BrowserManager:
    """Manages browser instances and automation tasks"""
    
    def __init__(self, browser_type: str = "chromium", headless: bool = True):
        self.browser_type = browser_type
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.executor = ThreadPoolExecutor(max_workers=3)
        
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
        
    def start(self) -> bool:
        """Start the browser manager"""
        if not PLAYWRIGHT_AVAILABLE:
            logging.error("Playwright is not available")
            return False
            
        try:
            self.playwright = sync_playwright().start()
            
            # Get browser based on type
            if self.browser_type.lower() == "chromium":
                self.browser = self.playwright.chromium.launch(headless=self.headless)
            elif self.browser_type.lower() == "firefox":
                self.browser = self.playwright.firefox.launch(headless=self.headless)
            elif self.browser_type.lower() == "webkit":
                self.browser = self.playwright.webkit.launch(headless=self.headless)
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")
            
            # Create context with common settings
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            logging.info(f"Browser manager started with {self.browser_type}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to start browser manager: {e}")
            return False
    
    def stop(self):
        """Stop the browser manager"""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            if self.executor:
                self.executor.shutdown(wait=True)
                
            logging.info("Browser manager stopped")
            
        except Exception as e:
            logging.error(f"Error stopping browser manager: {e}")
    
    def new_page(self) -> Optional[Page]:
        """Create a new page"""
        try:
            if not self.context:
                return None
            return self.context.new_page()
        except Exception as e:
            logging.error(f"Failed to create new page: {e}")
            return None
    
    def run_in_thread(self, func, *args, **kwargs):
        """Run a function in a separate thread to avoid asyncio conflicts"""
        future = self.executor.submit(func, *args, **kwargs)
        return future.result()


class WebScraper:
    """High-level web scraping interface"""
    
    def __init__(self, browser_type: str = "chromium", headless: bool = True):
        self.browser_manager = BrowserManager(browser_type, headless)
        
    def scrape_page(self, url: str, wait_for: str = None, timeout: int = 30000) -> Dict[str, Any]:
        """Scrape a single page and return structured data"""
        def _scrape():
            with self.browser_manager:
                page = self.browser_manager.new_page()
                if not page:
                    return {"error": "Failed to create page"}
                
                try:
                    # Navigate to page
                    page.goto(url, timeout=timeout)
                    
                    # Wait for specific element if specified
                    if wait_for:
                        page.wait_for_selector(wait_for, timeout=timeout)
                    
                    # Extract basic page data
                    result = {
                        "url": url,
                        "title": page.title(),
                        "content": page.content(),
                        "text": page.inner_text("body"),
                        "links": [],
                        "images": [],
                        "forms": [],
                        "meta": {}
                    }
                    
                    # Extract links
                    links = page.query_selector_all("a[href]")
                    for link in links:
                        href = link.get_attribute("href")
                        text = link.inner_text().strip()
                        if href:
                            result["links"].append({"href": href, "text": text})
                    
                    # Extract images
                    images = page.query_selector_all("img[src]")
                    for img in images:
                        src = img.get_attribute("src")
                        alt = img.get_attribute("alt") or ""
                        if src:
                            result["images"].append({"src": src, "alt": alt})
                    
                    # Extract forms
                    forms = page.query_selector_all("form")
                    for form in forms:
                        action = form.get_attribute("action") or ""
                        method = form.get_attribute("method") or "GET"
                        result["forms"].append({"action": action, "method": method})
                    
                    # Extract meta tags
                    meta_tags = page.query_selector_all("meta")
                    for meta in meta_tags:
                        name = meta.get_attribute("name") or meta.get_attribute("property")
                        content = meta.get_attribute("content")
                        if name and content:
                            result["meta"][name] = content
                    
                    return result
                    
                except Exception as e:
                    return {"error": f"Scraping failed: {str(e)}"}
                finally:
                    page.close()
        
        return self.browser_manager.run_in_thread(_scrape)
    
    def search_google(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google and return results"""
        def _search():
            with self.browser_manager:
                page = self.browser_manager.new_page()
                if not page:
                    return []
                
                try:
                    # Navigate to Google
                    page.goto("https://www.google.com")
                    
                    # Accept cookies if present
                    try:
                        page.click("button:has-text('Accept all')", timeout=2000)
                    except:
                        pass
                    
                    # Search
                    page.fill("input[name='q']", query)
                    page.press("input[name='q']", "Enter")
                    
                    # Wait for results
                    page.wait_for_selector("div#search", timeout=10000)
                    
                    # Extract search results
                    results = []
                    result_elements = page.query_selector_all("div.g")
                    
                    for i, element in enumerate(result_elements[:max_results]):
                        try:
                            title_elem = element.query_selector("h3")
                            link_elem = element.query_selector("a")
                            snippet_elem = element.query_selector("span:has-text('...')")
                            
                            if title_elem and link_elem:
                                title = title_elem.inner_text()
                                url = link_elem.get_attribute("href")
                                snippet = snippet_elem.inner_text() if snippet_elem else ""
                                
                                results.append({
                                    "title": title,
                                    "url": url,
                                    "snippet": snippet,
                                    "rank": i + 1
                                })
                        except Exception as e:
                            logging.warning(f"Failed to extract result {i}: {e}")
                            continue
                    
                    return results
                    
                except Exception as e:
                    logging.error(f"Google search failed: {e}")
                    return []
                finally:
                    page.close()
        
        return self.browser_manager.run_in_thread(_search)
    
    def search_google_maps(self, query: str, location: str = "", max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google Maps for businesses"""
        def _search_maps():
            with self.browser_manager:
                page = self.browser_manager.new_page()
                if not page:
                    return []
                
                try:
                    # Navigate to Google Maps
                    page.goto("https://www.google.com/maps")
                    
                    # Search query
                    search_query = f"{query} {location}".strip()
                    page.fill("input#searchboxinput", search_query)
                    page.press("input#searchboxinput", "Enter")
                    
                    # Wait for results
                    page.wait_for_selector("div[role='main']", timeout=15000)
                    
                    # Wait a bit more for results to load
                    page.wait_for_timeout(3000)
                    
                    # Extract business results
                    results = []
                    
                    # Try to find business listings
                    business_elements = page.query_selector_all("div[data-result-index]")
                    
                    for i, element in enumerate(business_elements[:max_results]):
                        try:
                            name_elem = element.query_selector("div.fontHeadlineSmall")
                            rating_elem = element.query_selector("span.MW4etd")
                            address_elem = element.query_selector("div:has-text('·')")
                            
                            name = name_elem.inner_text() if name_elem else f"Business {i+1}"
                            rating = rating_elem.inner_text() if rating_elem else "No rating"
                            address = address_elem.inner_text() if address_elem else "No address"
                            
                            results.append({
                                "name": name,
                                "rating": rating,
                                "address": address,
                                "query": search_query,
                                "rank": i + 1
                            })
                            
                        except Exception as e:
                            logging.warning(f"Failed to extract maps result {i}: {e}")
                            continue
                    
                    return results
                    
                except Exception as e:
                    logging.error(f"Google Maps search failed: {e}")
                    return []
                finally:
                    page.close()
        
        return self.browser_manager.run_in_thread(_search_maps)
    
    def extract_contact_info(self, url: str) -> Dict[str, Any]:
        """Extract contact information from a webpage"""
        def _extract():
            with self.browser_manager:
                page = self.browser_manager.new_page()
                if not page:
                    return {}
                
                try:
                    page.goto(url, timeout=30000)
                    
                    # Get page content
                    content = page.content()
                    text = page.inner_text("body")
                    
                    # Extract contact information using simple patterns
                    import re
                    
                    # Email patterns
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails = list(set(re.findall(email_pattern, text)))
                    
                    # Phone patterns
                    phone_pattern = r'(\+?1?[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
                    phones = list(set(re.findall(phone_pattern, text)))
                    phone_numbers = ['-'.join(filter(None, phone)) for phone in phones]
                    
                    # Social media links
                    social_links = []
                    social_patterns = {
                        'facebook': r'facebook\.com/[A-Za-z0-9._-]+',
                        'twitter': r'twitter\.com/[A-Za-z0-9._-]+',
                        'linkedin': r'linkedin\.com/[A-Za-z0-9._/-]+',
                        'instagram': r'instagram\.com/[A-Za-z0-9._-]+'
                    }
                    
                    for platform, pattern in social_patterns.items():
                        matches = re.findall(pattern, content)
                        for match in matches:
                            social_links.append({"platform": platform, "url": f"https://{match}"})
                    
                    return {
                        "url": url,
                        "emails": emails,
                        "phones": phone_numbers,
                        "social_links": social_links,
                        "title": page.title()
                    }
                    
                except Exception as e:
                    logging.error(f"Contact extraction failed: {e}")
                    return {"error": str(e)}
                finally:
                    page.close()
        
        return self.browser_manager.run_in_thread(_extract)


# Convenience functions for Project Chimera agents
def scrape_website(url: str, browser_type: str = "chromium") -> Dict[str, Any]:
    """Convenience function to scrape a website"""
    scraper = WebScraper(browser_type=browser_type, headless=True)
    return scraper.scrape_page(url)


def search_for_leads(query: str, location: str = "", max_results: int = 10) -> List[Dict[str, Any]]:
    """Convenience function to search for business leads"""
    scraper = WebScraper(browser_type="chromium", headless=True)
    return scraper.search_google_maps(query, location, max_results)


def extract_lead_contact_info(url: str) -> Dict[str, Any]:
    """Convenience function to extract contact info from a lead's website"""
    scraper = WebScraper(browser_type="chromium", headless=True)
    return scraper.extract_contact_info(url)
