import requests
from bs4 import BeautifulSoup
import json
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

urls = [
    "https://mp.weixin.qq.com/s/VzO-o7tchKeBB-i6pajvXg",
    "https://mp.weixin.qq.com/s/uny4wI8iQl3DKuGbklooHg",
    "https://mp.weixin.qq.com/s/keuF8xk8Ls9YB28G2V_d8Q",
    "https://mp.weixin.qq.com/s/wyBr6ztdYLHWifPc0fNVjw",
    "https://mp.weixin.qq.com/s/1aD0c-QumWNpe50kdnZwdw",
    "https://mp.weixin.qq.com/s/TO42RpTyGFRJEtFd8t6-yw",
    "https://mp.weixin.qq.com/s/PNLNyZ7KkO6W_PDI3TfSrw",
    "https://mp.weixin.qq.com/s/H7InlYLxwbGh5BuqBRP7tw",
    "https://mp.weixin.qq.com/s/nhvWUjU6G45QgAhcc6phuA",
    "https://mp.weixin.qq.com/s/YCH_Z7_6X4ZoZm4nwt0IrA",
    "https://mp.weixin.qq.com/s/FVEhYJmf2JL250_ldVoFVA",
    "https://mp.weixin.qq.com/s/RP2vBvN4J00SQfQ61lUYPA",
    "https://mp.weixin.qq.com/s/uw-WEIb6Low93eJa53cGNg",
    "https://mp.weixin.qq.com/s/wC8pW0c_H6HPILMKxYhscQ",
    "https://mp.weixin.qq.com/s/2rBSccP0MrfaMFBz75iscw",
    "https://mp.weixin.qq.com/s/sd7dWbHnWzGSAGS_K75Xjw",
    "https://mp.weixin.qq.com/s/YqHw-EmfN6_algXFcE_0wQ"
]

results = []
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://mp.weixin.qq.com/",
    "Connection": "keep-alive"
}

for i, url in enumerate(urls):
    logger.info(f"Scraping [{i+1}/{len(urls)}]: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        if "环境异常" in soup.text or "完成验证" in soup.text:
            logger.warning(f"Verification blocked: {url}")
            results.append({"url": url, "error": "Blocked by anti-scraping"})
        else:
            title_tag = soup.select_one("h1.rich_media_title")
            content_tag = soup.select_one("#js_content")
            
            title = title_tag.text.strip() if title_tag else "No Title"
            content = content_tag.text.strip() if content_tag else ""
            
            results.append({
                "url": url,
                "title": title,
                "content": content[:1500]
            })
    except Exception as e:
        logger.error(f"Failed {url}: {e}")
        results.append({"url": url, "error": str(e)})

with open("scraped_articles.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Scraping completed. Wrote to scraped_articles.json")
