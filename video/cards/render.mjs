import { createRequire } from 'module'; import fs from 'fs';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const tpl = fs.readFileSync(new URL('./card.html', import.meta.url), 'utf8');
const cards = JSON.parse(fs.readFileSync(new URL('./cards.json', import.meta.url), 'utf8'));
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
for (const c of cards) {
  const html = tpl.replace('__CLS__', c.dark ? 'dark' : '').replace('__EYEBROW__', c.eyebrow || '').replace('__TITLE__', c.title).replace('__SUB__', c.sub || '')
    .replace('__CHIPS__', (c.chips || []).map((x) => `<span class="chip">${x}</span>`).join('')).replace('__NOTE__', c.note || '');
  await p.setContent(html); await p.waitForTimeout(300);
  await p.screenshot({ path: new URL(`./${c.id}.png`, import.meta.url).pathname }); console.log('card', c.id);
}
await b.close();
