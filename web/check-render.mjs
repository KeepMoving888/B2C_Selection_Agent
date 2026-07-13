import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage();
page.on('console', (msg) => console.log('[console]', msg.type(), msg.text()));
page.on('pageerror', (err) => console.log('[pageerror]', err.message));
await page.goto('http://localhost:4177/verify-pdf.html');
await page.waitForTimeout(3000);
const hasRender = await page.evaluate(() => typeof window.renderPdf);
console.log('typeof renderPdf:', hasRender);
await page.screenshot({ path: 'verify-page.png' });
await browser.close();
