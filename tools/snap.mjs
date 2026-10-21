// Usage: node tools/snap.mjs outDir t1 t2 ... — screenshots the composition at given times (half-res)
import puppeteer from "puppeteer-core";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const root = path.resolve("video");
const types = { ".html": "text/html", ".js": "text/javascript", ".woff2": "font/woff2", ".ttf": "font/ttf", ".wav": "audio/wav" };
const srv = http.createServer((q, r) => { const f = path.join(root, decodeURIComponent(q.url.split("?")[0])); if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); } r.writeHead(200, { "content-type": types[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(r); }).listen(0);
const port = srv.address().port;
const [out, ...ts] = process.argv.slice(2); fs.mkdirSync(out, { recursive: true });
const b = await puppeteer.launch({ executablePath: "/opt/pw-browsers/chromium", args: ["--no-sandbox"] });
const p = await b.newPage(); await p.setViewport({ width: 2560, height: 1440, deviceScaleFactor: Number(process.env.DSF || 0.5) });
p.on("console", (m) => console.log("console:", m.text())); p.on("pageerror", (e) => console.log("ERR", e.message));
await p.goto(`http://localhost:${port}/index.html`, { waitUntil: "load" });
await p.evaluate(() => document.fonts.ready);
for (const t of ts) { await p.evaluate((t) => { window.__timelines.main.seek(Number(t)); }, t); await p.screenshot({ path: `${out}/t${String(t).padStart(5, "0")}.png` }); }
await b.close(); srv.close();
