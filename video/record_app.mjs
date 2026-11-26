// 実アプリを操作しながら録画する（1920x1080）。各操作と各処理段の完了時刻を marks.json に書く。
// usage: node record_app.mjs <outdir> [customerName]
import { createRequire } from 'module';
import fs from 'fs';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const [out = 'rec', who = ''] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1, recordVideo: { dir: out, size: { width: 1920, height: 1080 } } });
const p = await ctx.newPage();
const T0 = Date.now();
const marks = [];
const mark = (name, extra = {}) => { const t = (Date.now() - T0) / 1000; marks.push({ name, t, ...extra }); console.log(t.toFixed(1), name); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// 画面上にカーソルを表示（録画で操作が分かるように）
await p.addInitScript(() => {
  window.addEventListener('DOMContentLoaded', () => {
    const c = document.createElement('div');
    c.id = '__cur'; Object.assign(c.style, { position: 'fixed', left: '0px', top: '0px', width: '22px', height: '22px', borderRadius: '50%',
      background: 'rgba(255,54,33,.35)', border: '2px solid #FF3621', zIndex: 99999, pointerEvents: 'none', transform: 'translate(-50%,-50%)', transition: 'left .45s ease, top .45s ease' });
    document.body.appendChild(c);
    const z = () => { const r = document.getElementById('root'); if (r) r.style.zoom = '1.2'; else setTimeout(z, 50); }; z();
    document.addEventListener('mousemove', (e) => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; });
  });
});
async function moveClick(loc, pause = 700) {
  const bb = await loc.boundingBox();
  await p.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2, { steps: 18 }); await sleep(350);
  await loc.click(); await sleep(pause);
}
async function scrollTo(y) { await p.evaluate((y) => window.scrollTo({ top: y * 1.2, behavior: 'smooth' }), y); await sleep(900); }

await p.goto('http://localhost:8080', { waitUntil: 'networkidle' }); await sleep(2500);
mark('open');
// ① 顧客を選ぶ
const search = p.locator('.grid-survey .search');
await moveClick(search, 300);
if (who) { await p.keyboard.type(who, { delay: 120 }); await sleep(1500); }
await moveClick(p.locator('.grid-survey .pick-list li').first(), 1800);
mark('picked');
await scrollTo(380);
// 回答例「登山を始めた」
await moveClick(p.getByRole('button', { name: '登山を始めた' }), 1500);
mark('filled');
await scrollTo(700); await sleep(1500);
await scrollTo(380);
// 送信
await moveClick(p.getByRole('button', { name: '回答を送信する' }), 500);
mark('submitted');
await scrollTo(0);
// 処理の流れを待つ（各段の完了を記録）
const seen = new Set();
const t1 = Date.now();
while (Date.now() - t1 < 15 * 60_000) {
  const st = await p.evaluate(() => [...document.querySelectorAll('.node')].map((n) => (n.className.includes('done') ? 'd' : n.className.includes('running') ? 'r' : n.className.includes('error') ? 'e' : '-')).join(''));
  for (let i = 0; i < st.length; i++) if (st[i] === 'd' && !seen.has(i)) { seen.add(i); mark('node_done', { i }); }
  if (st.includes('e')) { mark('error'); break; }
  if (st[st.length - 1] === 'd') break;
  await sleep(500);
}
await sleep(2000);
// ② レコメンドの更新を見る
await moveClick(p.getByRole('button', { name: /顧客ごとのレコメンド/ }), 2500);
mark('customer');
await scrollTo(560); await sleep(2500);
mark('recos');
await p.mouse.move(1300, 760, { steps: 20 }); await sleep(2500);
await scrollTo(900); await sleep(2500);
mark('before');
await scrollTo(0); await sleep(1000);
// ③ 集計 ④ CustomerLake
await moveClick(p.getByRole('button', { name: /集計（Lakehouse/ }), 3000);
mark('summary');
await scrollTo(500); await sleep(2500); await scrollTo(0);
await moveClick(p.getByRole('button', { name: /CustomerLake/ }).last(), 3500);
mark('customerlake');
await sleep(3000);
mark('end');
const v = p.video();
await ctx.close(); await b.close();
fs.renameSync(await v.path(), `${out}/app.webm`);
fs.writeFileSync(`${out}/marks.json`, JSON.stringify(marks, null, 1));
