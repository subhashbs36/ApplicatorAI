import asyncio
from crawl4ai import *

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://careers.hpe.com/us/en/job/1182894/Hewlett-Packard-Labs---Machine-Learning-Research-Associate-Intern-Open?utm_source=linkedin",
        )
        print(result.markdown)

if __name__ == "__main__":
    asyncio.run(main())