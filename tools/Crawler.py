from typing import List, Dict, Any, Optional, Type, Union, Tuple
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import asyncio
import aiofiles
import re


class WebCrawler:
    """Class to handle web page crawling for job descriptions"""
    
    def __init__(self):
        self.max_concurrent = 1  # Only need one URL at a time for job descriptions
    
    async def crawl_url(self, url: str) -> str:
        """Crawl a single URL and return the content"""
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )
        crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

        crawler = AsyncWebCrawler(config=browser_config)
        await crawler.start()

        try:
            result = await crawler.arun(
                url=url,
                config=crawl_config,
                session_id="job_description"
            )
            if result.success:
                print(f"Successfully crawled: {url}")
                return result.markdown_v2.raw_markdown  # type: ignore
            else:
                print(f"Failed: {url} - Error: {result.error_message}")
                return f"Error crawling URL: {result.error_message}"
        finally:
            await crawler.close()
    
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
    
    def clean_job_description(self, content: str) -> str:
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