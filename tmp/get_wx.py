import urllib.request
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.in_content = False
        self.title = ""
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == "h1" and ("id", "activity-name") in attrs:
            self.in_title = True
        if tag == "div" and ("id", "js_content") in attrs:
            self.in_content = True

    def handle_endtag(self, tag):
        if tag == "h1" and self.in_title:
            self.in_title = False
        if tag == "div" and self.in_content:
            pass # simplistic, we just collect text

    def handle_data(self, data):
        data = data.strip()
        if not data: return
        if self.in_title:
            self.title += data
        elif self.in_content:
            self.text.append(data)

def fetch_wx(url):
    req = urllib.request.Request(
        url, 
        data=None, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    )
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
        parser = MyHTMLParser()
        parser.feed(html)
        print(f"URL: {url}")
        print(f"TITLE: {parser.title}")
        print(f"CONTENT PREVIEW:\n" + "\n".join(parser.text[:30]))
        print("==========")
    except Exception as e:
        print(f"Error for {url}: {e}")

urls = [
    "https://mp.weixin.qq.com/s/wC8pW0c_H6HPILMKxYhscQ",
    "https://mp.weixin.qq.com/s/2rBSccP0MrfaMFBz75iscw",
    "https://mp.weixin.qq.com/s/YqHw-EmfN6_algXFcE_0wQ",
    "https://mp.weixin.qq.com/s/sd7dWbHnWzGSAGS_K75Xjw"
]

for u in urls:
    fetch_wx(u)
