import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const logs = [];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  page.on('console', (msg) => {
    const text = msg.text();
    if (text.includes('[PDF]')) {
      logs.push(text);
      console.log(text);
    }
  });

  await page.goto('http://localhost:4181/report-center');
  await page.waitForTimeout(2000);

  // 生成示例报告
  await page.click('button:has-text("生成示例报告")');
  await page.waitForTimeout(2000);

  // 点击第一条详情
  await page.click('text=详情 >> nth=0');
  await page.waitForTimeout(1500);

  // 读取弹窗中行动计划的步骤数
  const actionSteps = await page.locator('.ant-modal .p-action, .ant-modal:has-text("七、行动计划")').count();
  console.log('Action steps in modal:', actionSteps);
  const actionHtml = await page.locator('.ant-modal').innerHTML();
  console.log('Has Week 5-6 in modal:', actionHtml.includes('Week 5-6'));
  console.log('Has 持续迭代 in modal:', actionHtml.includes('持续迭代'));

  // 截图查看弹窗
  await page.screenshot({ path: 'test-report-center.png', fullPage: true });

  // 导出 PDF（弹窗内的按钮）
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.locator('.ant-modal button:has-text("导出 PDF")').last().click(),
  ]);

  const downloadPath = await download.path();
  const savePath = path.join(process.cwd(), 'test-output.pdf');
  fs.copyFileSync(downloadPath, savePath);
  console.log('PDF saved to', savePath, 'size:', fs.statSync(savePath).size);
  console.log('All PDF logs:', logs.join('\n'));

  // 打开 PDF 并截图每一页
  const pdfPage = await context.newPage();
  await pdfPage.goto('file:///' + savePath.replace(/\\/g, '/'));
  await pdfPage.waitForTimeout(2000);
  const pageCount = await pdfPage.evaluate(() => document.querySelectorAll('.page').length || 1);
  console.log('PDF viewer page count:', pageCount);
  await pdfPage.screenshot({ path: 'test-pdf-page-last.png' });

  await browser.close();
})();
