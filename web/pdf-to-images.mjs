import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs';
import { createCanvas } from 'canvas';
import fs from 'fs';

pdfjs.GlobalWorkerOptions.disableWorker = true;

const data = new Uint8Array(fs.readFileSync('./test-output.pdf'));
const doc = await pdfjs.getDocument({ data }).promise;
console.log('Pages:', doc.numPages);

for (let i = 1; i <= doc.numPages; i++) {
  const page = await doc.getPage(i);
  const viewport = page.getViewport({ scale: 1.5 });
  const canvas = createCanvas(viewport.width, viewport.height);
  const ctx = canvas.getContext('2d');
  await page.render({ canvasContext: ctx, viewport }).promise;
  const buffer = canvas.toBuffer('image/png');
  fs.writeFileSync(`pdf-page-${i}.png`, buffer);
  console.log(`Saved pdf-page-${i}.png`);
}
