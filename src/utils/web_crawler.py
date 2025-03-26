from typing import List, Dict, Any, Optional, Type, Union, Tuple
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import asyncio
import aiofiles
import re
import random
from functools import lru_cache

class WebCrawler:
    """Class to handle web page crawling for job descriptions"""
    
    def __init__(self):
        self.max_concurrent = 1  # Only need one URL at a time for job descriptions
        self.max_retries = 3
        self.retry_delay = 2
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0'
        ]
        self._browser_config = self._create_browser_config()
        self._crawl_config = self._create_crawl_config()
    
    def _create_browser_config(self) -> BrowserConfig:
        """Create and cache browser configuration"""
        return BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                f"--user-agent={random.choice(self.user_agents)}",
                "--window-size=1920,1080"
            ],
        )

    def _create_crawl_config(self) -> CrawlerRunConfig:
        """Create and cache crawler configuration"""
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS
        )
    
    async def crawl_url(self, url: str) -> str:
        """Crawl a single URL and return the content"""
        for attempt in range(self.max_retries):
            crawler = AsyncWebCrawler(config=self._browser_config)
            await crawler.start()

            try:
                # Add delay between attempts
                if attempt > 0:
                    await asyncio.sleep(self.retry_delay * attempt)
                
                result = await crawler.arun(
                    url=url,
                    config=self._crawl_config,
                    session_id=f"job_description_{attempt}_{random.randint(1000, 9999)}",
                    headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0'
                    }
                )
                
                if result.success:
                    print(f"Successfully crawled: {url}")
                    # Handle different result formats safely
                    if hasattr(result, 'markdown') and result.markdown:
                        return result.markdown.raw_markdown
                    elif hasattr(result, 'text') and result.text:
                        return result.text
                    elif hasattr(result, 'html') and result.html:
                        return f"HTML content retrieved (no markdown available): {url}"
                    else:
                        return f"Content retrieved but format unknown: {url}"

                if "blocked" in str(result.error_message).lower():
                    print(f"Attempt {attempt + 1} blocked, retrying after delay...")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                
                print(f"Failed: {url} - Error: {result.error_message}")
                return f"Error crawling URL: {result.error_message}"

            except Exception as e:
                print(f"Attempt {attempt + 1} failed with error: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                return f"Error crawling URL after {self.max_retries} attempts: {str(e)}"

            finally:
                await crawler.close()

        return "Error: Maximum retry attempts reached"
    
    def fetch_job_description(self, url: str) -> str:
        """Synchronous wrapper for crawl_url"""
        if not url or not url.strip():
            return ""
            
        if not (url.startswith("http://") or url.startswith("https://")):
            return "Invalid URL. Please enter a URL starting with http:// or https://"
            
        try:
            return asyncio.run(self.crawl_url(url))
        except Exception as e:
            return f"Error crawling URL: {str(e)}"
    
    @staticmethod
    def clean_job_description(content: str) -> str:
        """Clean and format job description from crawled content"""
        if not content or content.startswith("Error"):
            return content
            
        # Remove any HTML or markdown formatting that might remain
        # Keep only the most relevant job description parts
        
        # Look for sections that might contain job description
        job_sections = []
        sections = re.split(r'\n#{1,3} ', content)
        
        keywords = ['job description', 'responsibilities', 'requirements', 
                   'qualifications', 'about the role', 'about the position',
                   'what you\'ll do', 'what we\'re looking for']
                   
        for section in sections:
            section_lower = section.lower()
            if any(keyword in section_lower for keyword in keywords):
                job_sections.append(section)
                
        # If we found specific job sections, use them
        if job_sections:
            processed_content = "\n\n".join(job_sections)
        else:
            # Otherwise, just use the whole content but try to clean it up
            processed_content = content
            
        # Remove any remaining markdown links
        processed_content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', processed_content)
        
        # Remove any extra whitespace
        processed_content = re.sub(r'\n{3,}', '\n\n', processed_content)
        
        return processed_content