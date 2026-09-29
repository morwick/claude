import { chromium } from 'playwright';
import path from 'path';
const times = process.argv.slice(2).map(Number);
const out = process.env.OUT || '/tmp/claude-0/stills';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args:['--allow-file-access-from-files'] });
const page = await browser.newPage({ viewport:{width:1080,height:1920}, deviceScaleFactor:1 });
page.on('console', m=>console.log('console:', m.text())); page.on('pageerror', e=>console.log('ERR', e.message));
await page.goto('file://'+path.resolve('index.html'));
await page.evaluate(()=>window.ready);
for (const t of times){ await page.evaluate(t=>window.render(t), t); await page.screenshot({path:`${out}/f_${t.toFixed(2)}.png`}); }
await browser.close();
