import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const base64 = fs.readFileSync('./test-output.pdf', 'base64');
const htmlPath = path.resolve('./verify-pdf.html');

const browser = await chromium.launch();
const page = await browser.newPage();
page.on('console', (msg) => console.log('[browser]', msg.text()));
page.on('pageerror', (err) => console.log('[pageerror]', err.message));
await page.goto('http://localhost:4181/verify-pdf.html');
await page.waitForFunction(() => typeof window.renderPdf === 'function', { timeout: 10000 });
const numPages = await page.evaluate(async (b64) => window.renderPdf(b64), base64);
console.log('Rendered pages:', numPages);

for (let i = 1; i <= numPages; i++) {
  await page.locator(`#page-${i}`).screenshot({ path: `pdf-page-${i}.png` });
  console.log('Saved pdf-page-' + i + '.png');
}

await browser.close();
