import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class WechatConnector:
    """
    Connector for WeChat Official Account articles.
    """
    
    @staticmethod
    def fetch_article(url):
        """
        Fetch and parse a WeChat Official Account article.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Check for verification or rate limit
            if "尝试太多" in response.text or "验证码" in response.text:
                logger.warning("WeChat rate limit detected")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title_tag = soup.find('h1', id='activity-name')
            title = title_tag.get_text(strip=True) if title_tag else "WeChat Article"
            
            # Extract author
            author_tag = soup.find('span', id='js_author_name')
            author = author_tag.get_text(strip=True) if author_tag else ""
            
            # Extract content HTML
            content_div = soup.find('div', id='js_content')
            if not content_div:
                # Try alternative content selectors
                content_div = soup.find('div', class_='rich_media_content') or \
                              soup.find('div', id='img-content') or \
                              soup.find('div', class_='rich_media_area_primary')
                
            if not content_div:
                return None
                
            # Clean up content: ONLY remove scripts, keep styles as they often contain layout info
            for script in content_div(["script"]):
                script.extract()
            
            # Remove WeChat specific components that often cause layout issues (like the "click to follow" widgets)
            for widget in content_div.find_all(class_=['qr_code_pc_outer', 'reward_area', 'js_ad_area']):
                widget.decompose()

            # Remove empty tags that cause weird spacing
            for empty_tag in content_div.find_all(['p', 'span', 'section']):
                # Check if tag is still in the tree
                if empty_tag.parent is None:
                    continue
                
                # Check if it's truly empty or just contains whitespace/line breaks
                text = empty_tag.get_text(strip=True)
                if not text and not empty_tag.find_all('img'):
                    style = empty_tag.get('style', '') or ''
                    if 'background' not in style:
                        empty_tag.decompose()

            # Process images: WeChat uses multiple attributes for images
            for img in content_div.find_all('img'):
                # Prefer data-src, then src
                actual_src = img.get('data-src') or img.get('src')
                if actual_src:
                    img['src'] = actual_src
                    # Set a style to ensure images don't overflow
                    img['style'] = "max-width: 100% !important; height: auto !important; margin: 10px 0; display: block;"
                    img['referrerpolicy'] = "no-referrer"
            
            # Process sections and other elements that might have hidden overflow or display:none
            for tag in content_div.find_all(['section', 'p', 'div', 'span', 'ul', 'li']):
                # Force remove list bullets which appear as "dots"
                if tag.name in ['ul', 'li']:
                    tag['style'] = tag.get('style', '') + "; list-style: none !important; list-style-type: none !important; margin-left: 0 !important; padding-left: 0 !important;"
                
                if tag.get('style'):
                    s = tag['style'].lower()
                    if 'visibility: hidden' in s:
                        tag['style'] = tag['style'].replace('visibility: hidden', 'visibility: visible')
                    if 'display: none' in s:
                        tag['style'] = tag['style'].replace('display: none', 'display: block')
            
            # Ensure code blocks and their containers are visible and well-styled
            for code_element in content_div.find_all(['pre', 'code']):
                # Find parent that might be hiding it
                parent = code_element.parent
                while parent and parent != content_div:
                    if parent.get('style'):
                        ps = parent['style'].lower()
                        if 'overflow' in ps or 'height' in ps:
                            parent['style'] = parent['style'] + "; overflow: visible !important; height: auto !important; max-height: none !important;"
                    parent = parent.parent
                
                # Differentiate between standalone code blocks and inline code
                is_block = code_element.name == 'pre' or (code_element.parent and code_element.parent.name == 'pre')
                
                if is_block:
                    code_element['style'] = "display: block !important; visibility: visible !important; opacity: 1 !important; background: #282c34 !important; color: #abb2bf !important; padding: 20px !important; border-radius: 8px !important; margin: 15px 0 !important; font-family: 'Fira Code', Consolas, Monaco, monospace !important; font-size: 13px !important; line-height: 1.6 !important; overflow-x: auto !important; white-space: pre !important; word-break: normal !important; border: none !important;"
                else:
                    # Inline code
                    code_element['style'] = "display: inline !important; background: #f3f3f3 !important; color: #e83e8c !important; padding: 2px 4px !important; border-radius: 3px !important; font-family: Consolas, Monaco, monospace !important; font-size: 90% !important; border: 1px solid #ddd !important;"
            
            # Special handling for tables to ensure they look like tables
            for table in content_div.find_all('table'):
                table['style'] = "width: 100% !important; border-collapse: collapse !important; margin: 20px 0 !important;"
                for td in table.find_all(['td', 'th']):
                    td['style'] = "border: 1px solid #ddd !important; padding: 8px !important; background: #fff !important; color: #333 !important; font-size: 14px !important;"
                for th in table.find_all('th'):
                    th['style'] += "background: #f5f7fa !important; font-weight: bold !important;"
            
            # Wrap content in a professional template
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta name="referrer" content="no-referrer">
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "PingFang SC", "Microsoft YaHei", "Source Han Sans SC", "Noto Sans CJK SC", WenQuanYi Micro Hei, sans-serif;
                        line-height: 1.8;
                        color: #333;
                        max-width: 750px;
                        margin: 0 auto;
                        padding: 30px 20px;
                        background: #fff;
                        word-wrap: break-word;
                        -webkit-font-smoothing: antialiased;
                    }}
                    h1 {{ font-size: 26px; font-weight: 700; margin-bottom: 16px; line-height: 1.4; color: #1a1a1a; }}
                    .author {{ font-size: 15px; color: #576b95; font-weight: 500; margin-bottom: 30px; }}
                    img {{ max-width: 100% !important; height: auto !important; display: block; margin: 20px auto; border-radius: 4px; }}
                    
                    /* Global resets to fix WeChat artifacts */
                    ul, li {{ list-style: none !important; padding: 0 !important; margin: 0 !important; }}
                    section, div, p {{ 
                        max-width: 100% !important; 
                        box-sizing: border-box !important; 
                        word-wrap: break-word !important;
                    }}
                    
                    /* Code block styling */
                    pre, code {{ 
                        white-space: pre !important;
                        word-break: normal !important;
                        word-wrap: normal !important;
                    }}
                    .article-content {{ font-size: 16px; color: #3e3e3e; }}
                    p {{ margin-bottom: 1.5em; }}
                    
                    pre {{ padding: 10px; overflow-x: auto; white-space: pre !important; word-wrap: normal !important; }}
                    section {{ max-width: 100% !important; box-sizing: border-box !important; }}
                    
                    /* Table styling */
                    table {{
                        width: 100% !important;
                        border-collapse: collapse !important;
                        margin: 20px 0 !important;
                        border: 1px solid #ebeef5 !important;
                        table-layout: auto !important;
                    }}
                    th, td {{
                        border: 1px solid #ebeef5 !important;
                        padding: 12px !important;
                        text-align: left !important;
                        word-break: break-all !important;
                    }}
                    th {{
                        background-color: #f5f7fa !important;
                        font-weight: 700 !important;
                    }}

                    /* Hide those pesky dots if they are spans or empty elements */
                    .code-snippet__line-index {{ display: none !important; }}
                </style>
            </head>
            <body>
                <h1>{title}</h1>
                <div class="author">{author}</div>
                <div class="article-content">
                    {content_div.decode_contents()}
                </div>
            </body>
            </html>
            """
            
            return {
                "title": title,
                "author": author,
                "content": html_content,
                "text_content": content_div.get_text(separator='\n', strip=True),
                "url": url
            }
        except Exception as e:
            import traceback
            logger.error(f"Error fetching WeChat article: {e}\n{traceback.format_exc()}")
            return None
