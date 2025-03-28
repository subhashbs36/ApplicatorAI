from typing import List, Dict, Any, Optional, Type, Union, Tuple
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import asyncio
import aiofiles
import re
import random
from functools import lru_cache
from pathlib import Path
import os
import hashlib

class WebCrawler:
    """Class to handle web page crawling for job descriptions"""
    
    def __init__(self):
        self.max_concurrent = 1  # Only need one URL at a time for job descriptions
        self.max_retries = 3
        self.retry_delay = 1  # Reduced from 2 to 1 second
        self._browser_config = self._create_browser_config()
        self._crawl_config = self._create_crawl_config()
        
        # Set up paths for caching
        self.base_path = Path(__file__).parent.parent.parent
        self.data_path = self.base_path / "src" / "data"
        self.cache_path = self.data_path / "cache"
        
        # Create directories if they don't exist
        os.makedirs(self.cache_path, exist_ok=True)
    
    def _create_browser_config(self) -> BrowserConfig:
        """Create and cache browser configuration"""
        return BrowserConfig(
            browser_type="firefox",
            headless=True,
            verbose=False,  # Disabled verbose logging for better performance
            user_agent="random",
            viewport_width=1280,
            viewport_height=720,
            text_mode=True,
            extra_args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )
    
    def _create_crawl_config(self) -> CrawlerRunConfig:
        """Create and cache crawler configuration"""
        return CrawlerRunConfig(
            prettiify=True,
            exclude_external_links=True,
            cache_mode=CacheMode.BYPASS,
            exclude_social_media_links=True,
            remove_overlay_elements=True,
            excluded_tags=["nav", "footer"],            
        )
    
    def _clean_content_for_cache(self, content: str) -> str:
        """Clean the content before saving to cache to remove unwanted elements"""
        # Remove footer sections that often contain unwanted links
        footer_patterns = [
            r'(?i)<footer.*?>.*?</footer>',
            r'(?i)<!-- footer.*?-->.*?<!-- end footer -->',
            r'(?i)---+\s*footer\s*---+.*?(?=\n\n|\Z)',
            r'(?i)## footer.*?(?=\n##|\Z)',
        ]
        
        for pattern in footer_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        # Remove navigation, cookie notices, and other common unwanted elements
        unwanted_sections = [
            r'(?i)<nav.*?>.*?</nav>',
            r'(?i)cookie policy.*?(?=\n\n|\Z)',
            r'(?i)privacy policy.*?(?=\n\n|\Z)',
            r'(?i)terms of (use|service).*?(?=\n\n|\Z)',
            r'(?i)copyright ©.*?(?=\n\n|\Z)',
            r'(?i)all rights reserved.*?(?=\n\n|\Z)',
            r'(?i)follow us on.*?(?=\n\n|\Z)',
            r'(?i)share this job.*?(?=\n\n|\Z)',
        ]
        
        for pattern in unwanted_sections:
            content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        # Remove social media links and icons
        content = re.sub(r'(?i)(facebook|twitter|linkedin|instagram|youtube)\.com', '', content)
        
        # Remove excessive newlines while preserving paragraph structure
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
    
    async def crawl_url(self, url: str) -> str:
        """Crawl a single URL and return the content"""
        # Check if we have a cached version
        cache_file = self._get_cache_file_path(url)
        if cache_file.exists():
            async with aiofiles.open(cache_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                print(f"Using cached content for: {url}")
                return content
                
        crawler = None
        for attempt in range(self.max_retries):
            try:
                # Add minimal delay between attempts
                if attempt > 0:
                    print(f"Retrying {attempt+1}/{self.max_retries} for URL: {url}")
                    await asyncio.sleep(self.retry_delay * attempt)
                
                crawler = AsyncWebCrawler(config=self._browser_config)
                await crawler.start()
                
                # Removed unnecessary sleep after browser start
                
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
                    # Handle different result formats safely
                    if hasattr(result, 'markdown') and result.markdown_v2:
                        content = result.markdown_v2.raw_markdown
                        # Clean content before saving to cache
                        cleaned_content = self._clean_content_for_cache(content)
                        # Save to cache
                        await self._save_to_cache(url, cleaned_content)
                        # Ensure browser is properly closed before returning
                        await crawler.close()
                        return cleaned_content
                    elif hasattr(result, 'text') and result.text:
                        content = result.text
                        # Clean content before saving to cache
                        cleaned_content = self._clean_content_for_cache(content)
                        # Save to cache
                        await self._save_to_cache(url, cleaned_content)
                        await crawler.close()
                        return cleaned_content
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
            
        # Look for sections that might contain job description
        job_sections = []
        sections = re.split(r'\n#{1,3} ', content)
        
        # Expanded keywords to include title and company info
        keywords = [
            'job title', 'company', 'location',  # Added job metadata keywords
            'job description', 'responsibilities', 'requirements', 
            'qualifications', 'about the role', 'about the position',
            'what you\'ll do', 'what we\'re looking for', 'overview',
            'about us', 'about the company', 'position summary', 'jobs-details'
        ]
                   
        for section in sections:
            section_lower = section.lower()
            # Keep sections with keywords or the first section (usually contains title)
            if any(keyword in section_lower for keyword in keywords) or section == sections[0]:
                job_sections.append(section)
                
        # If we found specific job sections, use them
        if job_sections:
            processed_content = "\n\n".join(job_sections)
        else:
            # Otherwise, just use the whole content but try to clean it up
            processed_content = content
            
        # Remove any remaining markdown links
        processed_content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', processed_content)
        
        # Remove any extra whitespace while preserving paragraph structure
        processed_content = re.sub(r'\n{3,}', '\n\n', processed_content).strip()
        
        # Limit to first 100 lines before saving
        content_lines = processed_content.splitlines()
        limited_content = '\n'.join(content_lines[:100])
        
        # Save the cleaned job description to a cache file
        # Note: This is a static method, so we need to create a unique filename
        # without access to self.cache_path
        try:
            # Generate a unique filename based on content hash
            content_hash = hashlib.md5(limited_content.encode()).hexdigest()
            base_path = Path(__file__).parent.parent.parent
            cache_path = base_path / "src" / "data" / "cache"
            cache_file = cache_path / f"cleaned_{content_hash}.md"
            
            # Ensure the cache directory exists
            os.makedirs(cache_path, exist_ok=True)
            
            # Save the cleaned content to the cache file
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write("<!-- Cleaned Job Description -->\n\n")
                f.write(limited_content)
            print(f"Saved cleaned job description to cache: {cache_file}")
        except Exception as e:
            print(f"Error saving cleaned job description to cache: {str(e)}")
            
        return limited_content

    def _get_cache_file_path(self, url: str) -> Path:
        """Generate a unique filename for the URL cache"""
        # Create a hash of the URL to use as filename
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_path / f"{url_hash}.md"
    
    async def _save_to_cache(self, url: str, content: str) -> None:
        """Save the crawled content to a markdown file"""
        cache_file = self._get_cache_file_path(url)
        try:
            async with aiofiles.open(cache_file, 'w', encoding='utf-8') as f:
                # Add URL as a comment at the top of the file
                await f.write(f"<!-- Source URL: {url} -->\n\n")
                await f.write(content)
            print(f"Saved content to cache: {cache_file}")
        except Exception as e:
            print(f"Error saving to cache: {str(e)}")