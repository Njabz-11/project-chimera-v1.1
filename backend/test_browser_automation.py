#!/usr/bin/env python3
"""
Test script for browser automation infrastructure
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from infrastructure.browser_automation import WebScraper, BrowserManager, scrape_website, search_for_leads

def test_browser_manager():
    """Test basic browser manager functionality"""
    print("Testing Browser Manager...")
    
    try:
        with BrowserManager("chromium", headless=True) as manager:
            page = manager.new_page()
            if page:
                page.goto("https://httpbin.org/html")
                title = page.title()
                print(f"✅ Browser Manager: Page title = '{title}'")
                page.close()
                return True
            else:
                print("❌ Browser Manager: Failed to create page")
                return False
                
    except Exception as e:
        print(f"❌ Browser Manager failed: {e}")
        return False

def test_web_scraper():
    """Test web scraper functionality"""
    print("\nTesting Web Scraper...")
    
    try:
        scraper = WebScraper("chromium", headless=True)
        result = scraper.scrape_page("https://httpbin.org/html")
        
        if "error" in result:
            print(f"❌ Web Scraper failed: {result['error']}")
            return False
        
        print(f"✅ Web Scraper: Scraped page with title '{result.get('title', 'No title')}'")
        print(f"   - Found {len(result.get('links', []))} links")
        print(f"   - Found {len(result.get('images', []))} images")
        print(f"   - Content length: {len(result.get('content', ''))}")
        return True
        
    except Exception as e:
        print(f"❌ Web Scraper failed: {e}")
        return False

def test_google_search():
    """Test Google search functionality"""
    print("\nTesting Google Search...")
    
    try:
        scraper = WebScraper("chromium", headless=True)
        results = scraper.search_google("Python programming", max_results=3)
        
        if not results:
            print("❌ Google Search: No results returned")
            return False
        
        print(f"✅ Google Search: Found {len(results)} results")
        for i, result in enumerate(results[:2]):
            print(f"   {i+1}. {result.get('title', 'No title')}")
        return True
        
    except Exception as e:
        print(f"❌ Google Search failed: {e}")
        return False

def test_convenience_functions():
    """Test convenience functions"""
    print("\nTesting Convenience Functions...")
    
    try:
        # Test scrape_website
        result = scrape_website("https://httpbin.org/html")
        if "error" in result:
            print(f"❌ scrape_website failed: {result['error']}")
            return False
        
        print(f"✅ scrape_website: Success - {result.get('title', 'No title')}")
        return True
        
    except Exception as e:
        print(f"❌ Convenience functions failed: {e}")
        return False

def test_dependencies():
    """Test if Playwright is properly installed"""
    print("Testing Playwright Dependencies...")
    
    try:
        from playwright.sync_api import sync_playwright
        print("✅ Playwright sync_api available")
        
        from playwright.async_api import async_playwright
        print("✅ Playwright async_api available")
        
        return True
        
    except ImportError as e:
        print(f"❌ Playwright not available: {e}")
        return False

if __name__ == "__main__":
    print("=== Project Chimera Browser Automation Infrastructure Test ===")
    
    # Test dependencies first
    if not test_dependencies():
        print("\n❌ Dependencies not available - skipping tests")
        exit(1)
    
    # Run tests
    tests = [
        test_browser_manager,
        test_web_scraper,
        test_google_search,
        test_convenience_functions
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print(f"\n=== Test Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 All browser automation tests passed!")
    else:
        print("⚠️ Some tests failed - check the output above")
