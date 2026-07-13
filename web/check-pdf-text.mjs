import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs';
import fs from 'fs';

pdfjs.GlobalWorkerOptions.disableWorker = true;

const data = new Uint8Array(fs.readFileSync('./test-output.pdf'));
const doc = await pdfjs.getDocument({ data }).promise;
console.log('Pages:', doc.numPages);

for (let i = 1; i <= doc.numPages; i++) {
  const page = await doc.getPage(i);
  const text = await page.getTextContent();
  const str = text.items.map((item) => item.str).join('');
  console.log(`\n--- Page ${i} ---`);
  console.log('Length:', str.length);
  console.log('Has Week 1-2:', str.includes('Week 1-2'));
  console.log('Has Week 3-4:', str.includes('Week 3-4'));
  console.log('Has 备货与物流布局:', str.includes('备货与物流布局'));
  console.log('Has Listing 优化:', str.includes('Listing 优化'));
  console.log('Has 持续迭代:', str.includes('持续迭代'));
  console.log(str.slice(0, 800));
}
