import { PDFDocument } from 'pdf-lib';
import fs from 'fs';

const bytes = fs.readFileSync('./test-output.pdf');
const pdf = await PDFDocument.load(bytes);
console.log('Pages:', pdf.getPageCount());
console.log('File size:', bytes.length);

// pdf-lib 提取文本较复杂，这里简单检查 PDF 页面尺寸
for (let i = 0; i < pdf.getPageCount(); i++) {
  const page = pdf.getPage(i);
  const { width, height } = page.getSize();
  console.log(`Page ${i + 1}: ${width}x${height}`);
}
