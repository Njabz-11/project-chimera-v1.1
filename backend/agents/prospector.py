"""
Project Chimera - Prospector Agent (SCOUT)
Autonomously finds and qualifies leads on the open internet using browser automation and LLM extraction
"""

import os
import json
import asyncio
import random
import time
import sys
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus, urljoin
import logging

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
import concurrent.futures
from bs4 import BeautifulSoup

# Fix Windows event loop policy for Playwright
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from .base_agent import BaseAgent, AgentJob, AgentResult
from utils.llm_service import llm_service

class ProspectorAgent(BaseAgent):
    """SCOUT - Lead discovery and qualification specialist"""

    def __init__(self, db_manager):
        super().__init__("SCOUT", db_manager)
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

        # Configuration from environment
        self.scraping_delay_min = int(os.getenv("SCRAPING_DELAY_MIN", "1"))
        self.scraping_delay_max = int(os.getenv("SCRAPING_DELAY_MAX", "3"))
        self.user_agent = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        self.max_leads_per_search = int(os.getenv("MAX_LEADS_PER_SEARCH", "50"))

    async def execute(self, job: AgentJob) -> AgentResult:
        """Execute prospector-specific jobs"""
        start_time = time.time()

        try:
            job_type = job.input_data.get("type", "find_leads")

            if job_type == "find_leads":
                result = await self._find_leads(job.input_data)
            else:
                result = {"error": f"Unknown job type: {job_type}"}

            execution_time = int((time.time() - start_time) * 1000)

            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="success" if "error" not in result else "error",
                output_data=result,
                execution_time_ms=execution_time
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f"Prospector execution failed: {str(e)}"
            self.logger.error(error_msg)

            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={"error": error_msg},
                execution_time_ms=execution_time
            )

    async def _find_leads(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Find leads based on search criteria"""

        search_query = job_data.get("search_query", "")
        mission_id = job_data.get("mission_id")
        search_sources = job_data.get("sources", ["google_maps", "google_search"])

        if not search_query:
            return {"error": "No search query provided"}

        self.logger.info(f"Starting lead search for: {search_query}")

        all_leads = []
        search_results = {}

        try:
            # Run browser operations in a separate thread to avoid asyncio conflicts
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._run_browser_search, search_query, search_sources)
                search_result = future.result()

                # Get scraped content for LLM processing
                scraped_content = search_result.get("scraped_content", {})
                search_results = search_result.get("search_results", {})

                # Process scraped content with LLM to extract real leads
                all_leads = []
                for source, content_data in scraped_content.items():
                    if content_data and content_data.get("content"):
                        extraction_result = await llm_service.extract_lead_data(
                            content_data["content"],
                            content_data["search_query"]
                        )

                        if extraction_result.get("leads"):
                            for lead in extraction_result["leads"]:
                                lead["lead_source"] = source
                                all_leads.append(lead)

                        self.logger.info(f"{source} LLM extraction found {len(extraction_result.get('leads', []))} leads")

            # Remove duplicates based on company name
            unique_leads = self._deduplicate_leads(all_leads)

            # Save leads to database
            saved_leads = []
            for lead_data in unique_leads[:self.max_leads_per_search]:
                try:
                    lead_data["mission_id"] = mission_id
                    lead_data["lead_source"] = "prospector_agent"
                    lead_data["status"] = "new"

                    lead_id = await self.db_manager.create_lead(lead_data)
                    lead_data["id"] = lead_id
                    saved_leads.append(lead_data)

                    self.logger.info(f"Saved lead: {lead_data.get('company_name', 'Unknown')}")

                except Exception as e:
                    self.logger.error(f"Failed to save lead: {e}")

            return {
                "search_query": search_query,
                "sources_searched": search_results,
                "total_found": len(all_leads),
                "unique_leads": len(unique_leads),
                "saved_leads": len(saved_leads),
                "leads": saved_leads
            }

        except Exception as e:
            error_msg = f"Lead search failed: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}

        finally:
            pass  # Cleanup handled in thread

    def _run_browser_search(self, search_query: str, search_sources: List[str]) -> Dict[str, Any]:
        """Run browser search in a separate thread to avoid asyncio conflicts"""
        search_results = {}
        self._scraped_content = {}

        try:
            # Initialize browser
            self._init_browser()

            # Search different sources
            for source in search_sources:
                if source == "google_maps":
                    self._search_google_maps_sync(search_query)
                    search_results["google_maps"] = 1  # Scraped successfully
                elif source == "google_search":
                    self._search_google_sync(search_query)
                    search_results["google_search"] = 1  # Scraped successfully

                # Add delay between searches
                time.sleep(random.uniform(self.scraping_delay_min, self.scraping_delay_max))

            return {
                "scraped_content": self._scraped_content,
                "search_results": search_results
            }

        except Exception as e:
            self.logger.error(f"Browser search failed: {e}")
            return {
                "scraped_content": {},
                "search_results": {},
                "error": str(e)
            }

        finally:
            self._cleanup_browser()

    def _init_browser(self):
        """Initialize Playwright browser with Windows compatibility using sync API"""
        if not self.browser:
            try:
                self.playwright = sync_playwright().start()

                # Launch browser with Windows-compatible settings
                self.browser = self.playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )

                self.context = self.browser.new_context(
                    user_agent=self.user_agent,
                    viewport={'width': 1920, 'height': 1080},
                    ignore_https_errors=True
                )

                self.page = self.context.new_page()

                # Set reasonable timeouts
                self.page.set_default_timeout(30000)  # 30 seconds

                self.logger.info("✅ Browser initialized successfully")

            except Exception as e:
                self.logger.error(f"Failed to initialize browser: {e}")
                raise

    def _cleanup_browser(self):
        """Clean up browser resources"""
        try:
            if self.page:
                self.page.close()
                self.page = None
            if self.context:
                self.context.close()
                self.context = None
            if self.browser:
                self.browser.close()
                self.browser = None
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()
                self.playwright = None
            self.logger.info("✅ Browser cleanup completed")
        except Exception as e:
            self.logger.error(f"Error cleaning up browser: {e}")

    async def _random_delay(self):
        """Add random delay to avoid being detected as bot"""
        delay = random.uniform(self.scraping_delay_min, self.scraping_delay_max)
        await asyncio.sleep(delay)

    async def _search_google_maps(self, search_query: str) -> List[Dict[str, Any]]:
        """Search Google Maps for businesses"""
        leads = []

        try:
            # Navigate to Google Maps
            maps_url = f"https://www.google.com/maps/search/{quote_plus(search_query)}"
            self.page.goto(maps_url, wait_until="networkidle")

            # Wait for results to load
            self.page.wait_for_timeout(3000)

            # Get page content
            content = self.page.content()

            # Extract leads using LLM
            extraction_result = await llm_service.extract_lead_data(content, search_query)

            if extraction_result.get("leads"):
                for lead in extraction_result["leads"]:
                    lead["lead_source"] = "google_maps"
                    leads.append(lead)

            self.logger.info(f"Google Maps search found {len(leads)} potential leads")

        except Exception as e:
            self.logger.error(f"Google Maps search failed: {e}")

        return leads

    def _search_google_maps_sync(self, search_query: str):
        """Search Google Maps for businesses (synchronous version)"""

        try:
            # Navigate to Google Maps
            maps_url = f"https://www.google.com/maps/search/{quote_plus(search_query)}"
            self.page.goto(maps_url, wait_until="networkidle")

            # Wait for results to load
            self.page.wait_for_timeout(3000)

            # Get page content
            content = self.page.content()

            # Store content for async LLM processing
            self._scraped_content["google_maps"] = {
                "content": content,
                "search_query": search_query
            }

            self.logger.info(f"Google Maps content scraped successfully for: {search_query}")

        except Exception as e:
            self.logger.error(f"Google Maps search failed: {e}")

    def _search_google_sync(self, search_query: str):
        """Search Google for businesses (synchronous version)"""

        try:
            # Navigate to Google Search
            google_url = f"https://www.google.com/search?q={quote_plus(search_query + ' business contact')}"
            self.page.goto(google_url, wait_until="networkidle")

            # Wait for results to load
            self.page.wait_for_timeout(2000)

            # Get page content
            content = self.page.content()

            # Store content for async LLM processing
            self._scraped_content["google_search"] = {
                "content": content,
                "search_query": search_query
            }

            self.logger.info(f"Google search content scraped successfully for: {search_query}")

        except Exception as e:
            self.logger.error(f"Google search failed: {e}")

    async def _search_google(self, search_query: str) -> List[Dict[str, Any]]:
        """Search Google for businesses"""
        leads = []

        try:
            # Navigate to Google Search
            google_url = f"https://www.google.com/search?q={quote_plus(search_query + ' business contact')}"
            self.page.goto(google_url, wait_until="networkidle")

            # Wait for results to load
            self.page.wait_for_timeout(2000)

            # Get page content
            content = self.page.content()

            # Extract leads using LLM
            extraction_result = await llm_service.extract_lead_data(content, search_query)

            if extraction_result.get("leads"):
                for lead in extraction_result["leads"]:
                    lead["lead_source"] = "google_search"
                    leads.append(lead)

            self.logger.info(f"Google search found {len(leads)} potential leads")

        except Exception as e:
            self.logger.error(f"Google search failed: {e}")

        return leads

    def _deduplicate_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate leads based on company name"""
        seen_companies = set()
        unique_leads = []

        for lead in leads:
            company_name = lead.get("company_name", "").lower().strip()
            if company_name and company_name not in seen_companies:
                seen_companies.add(company_name)
                unique_leads.append(lead)

        return unique_leads

    async def __aenter__(self):
        """Async context manager entry"""
        self._init_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self._cleanup_browser()
