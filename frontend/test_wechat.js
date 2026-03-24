const puppeteer = require('puppeteer');

(async () => {
    try {
        const browser = await puppeteer.launch({ headless: 'new' });
        const page = await browser.newPage();
        
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36');
        
        console.log("Navigating to WeChat article...");
        await page.goto('https://mp.weixin.qq.com/s/Pfl16RCDA89cQ9A-eqNljQ', { waitUntil: 'networkidle2', timeout: 30000 });
        
        const content = await page.evaluate(() => {
            const article = document.querySelector('#js_content');
            if (article) {
                return article.innerText;
            }
            return document.body.innerText;
        });

        console.log("=== ARTICLE CONTENT START ===");
        console.log(content.substring(0, 20000)); // Print up to 20000 chars
        console.log("=== ARTICLE CONTENT END ===");

        const title = await page.title();
        console.log("Title:", title);
        
        await browser.close();
    } catch (e) {
        console.error("Error:", e);
    }
})();
