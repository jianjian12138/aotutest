const { PuppeteerAgent } = require('@midscene/web/puppeteer');
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// 获取命令行参数
const args = process.argv.slice(2);
const instruction = args[0]; // 自然语言指令
const outputDir = args[1]; // 输出目录
const taskId = args[2]; // 任务ID

if (!instruction || !outputDir || !taskId) {
  console.error('Usage: node midscene_runner.js <instruction> <outputDir> <taskId>');
  process.exit(1);
}

// 确保输出目录存在
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

(async () => {
  let browser;
  try {
    console.log(JSON.stringify({ type: 'log', level: 'info', message: '正在启动浏览器...' }));
    
    browser = await puppeteer.launch({
      headless: false, // 有头模式，方便调试，服务器上通常设为 true
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });

    console.log(JSON.stringify({ type: 'log', level: 'info', message: '初始化 Midscene Agent...' }));
    
    // 初始化 Midscene Agent
    const agent = new PuppeteerAgent(page);

    console.log(JSON.stringify({ type: 'log', level: 'info', message: `开始执行指令: ${instruction}` }));

    // 执行自然语言指令
    // 注意：midscene 现在的版本 API 可能是 .aiAction 或者 .ai()，这里假设是 .aiAction
    // 如果是 0.1.1 版本，可能 API 不同。但刚才安装了最新版 @midscene/web
    await agent.aiAction(instruction);

    console.log(JSON.stringify({ type: 'log', level: 'success', message: '指令执行完成' }));

    // 截图
    const screenshotPath = path.join(outputDir, `${taskId}.png`);
    await page.screenshot({ path: screenshotPath });
    
    // 生成相对路径用于前端访问
    // 假设 outputDir 是 d:\TEST\media\midscene_screenshots
    // 前端访问路径应该是 /media/midscene_screenshots/taskId.png
    const mediaPath = `/media/midscene_screenshots/${taskId}.png`;

    // 输出最终结果
    console.log(JSON.stringify({
      type: 'result',
      status: 'success',
      screenshot_url: mediaPath,
      video_url: null, // 暂不支持视频
      logs: '执行成功'
    }));

  } catch (error) {
    console.error(JSON.stringify({ type: 'log', level: 'error', message: error.message }));
    
    // 尝试截图错误现场
    try {
        if (browser) {
            const pages = await browser.pages();
            if (pages.length > 0) {
                const screenshotPath = path.join(outputDir, `${taskId}_error.png`);
                await pages[0].screenshot({ path: screenshotPath });
            }
        }
    } catch (e) {
        // ignore screenshot error
    }

    console.log(JSON.stringify({
      type: 'result',
      status: 'failed',
      error: error.message,
      screenshot_url: `/media/midscene_screenshots/${taskId}_error.png`
    }));
  } finally {
    if (browser) {
      await browser.close();
    }
  }
})();
