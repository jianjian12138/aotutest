import urllib.request
from bs4 import BeautifulSoup

urls = [
    "https://mp.weixin.qq.com/s/wC8pW0c_H6HPILMKxYhscQ",
    "https://mp.weixin.qq.com/s/2rBSccP0MrfaMFBz75iscw",
    "https://mp.weixin.qq.com/s/YqHw-EmfN6_algXFcE_0wQ",
    "https://mp.weixin.qq.com/s/sd7dWbHnWzGSAGS_K75Xjw"
]

for i, url in enumerate(urls):
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
        )
        html = urllib.request.urlopen(req).read().decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        
        title_tag = soup.find('h1', id='activity-name')
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        
        content_div = soup.find('div', id='js_content')
        content = content_div.get_text(separator='\n', strip=True) if content_div else "No Content"
        
        print(f"Saved {url} to tmp/wx_{i}.txt")
        with open(f"tmp/wx_{i}.txt", "w", encoding="utf-8") as f:
            f.write(f"URL: {url}\nTITLE: {title}\n\nCONTENT:\n{content}")
    except Exception as e:
        print(f"Error for {url}: {e}")
