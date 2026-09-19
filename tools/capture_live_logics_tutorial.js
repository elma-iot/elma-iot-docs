#!/usr/bin/env node
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

let baseUrl = process.argv[2] || "fixture";
const outputRoot = process.argv[3] || path.resolve(__dirname, "../assets/screenshots/web");
let fixtureServer = null;
if (baseUrl === "fixture") {
  const firmwareRoot = path.resolve(__dirname, "../../Firmware");
  const webRoot = path.join(firmwareRoot, "web");
  const defaults = JSON.parse(fs.readFileSync(path.join(firmwareRoot, ".elma-project-defaults.json"), "utf8"));
  const graph = defaults.compiledLogic;
  const logics = {
    mode: graph.mode || "playing", updating: false, graph,
    groups: graph.groups || [], audioEnabled: true,
    live: {
      values: { "cpu-temperature": { value: 56.2 }, "above-50": { result: true } },
      activity: {
        "beep-every-5s": { sequence: 4, at: 25000, failed: false },
        "buzzer-beep": { sequence: 4, at: 25000, failed: false },
      }, error: "",
    },
  };
  const contentTypes = { ".html": "text/html", ".js": "application/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".ico": "image/x-icon" };
  fixtureServer = http.createServer((request, response) => {
    const pathname = new URL(request.url, "http://localhost").pathname;
    if (pathname === "/api/logics") return void response.end(JSON.stringify(logics));
    if (pathname === "/api/status") return void response.end(JSON.stringify({
      device: { deviceName: "elma-demo", friendlyName: "ELMA Demo" },
      network: { wifiConnected: true, mqttConnected: true, ip: "192.168.1.100", wifiRssi: -55 },
      playback: { state: "idle", title: "Idle" }, battery: { voltage: 0.2 },
      firmware: { version: "0.1.55", audioEnabled: true },
      system: { chipTemperatureAvailable: true, chipTemperatureC: 56.2 },
    }));
    if (pathname === "/api/settings") return void response.end(JSON.stringify({ ui: { language: "ru", theme: "dark" } }));
    if (pathname.startsWith("/api/")) { response.statusCode = 404; return void response.end("{}"); }
    const relative = pathname === "/" ? "index.html" : pathname.replace(/^\//, "");
    const file = path.resolve(webRoot, relative);
    if (!file.startsWith(webRoot) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { response.statusCode = 404; return void response.end("Not found"); }
    response.setHeader("Content-Type", contentTypes[path.extname(file)] || "application/octet-stream");
    response.end(fs.readFileSync(file));
  });
  fixtureServer.listen(9345, "127.0.0.1");
  baseUrl = "http://127.0.0.1:9345";
}
const chrome = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const profile = path.join(process.env.TEMP || ".", `elma-logics-capture-${process.pid}`);
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitJson(url) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try { return await (await fetch(url)).json(); } catch { await delay(250); }
  }
  throw new Error(`Timed out waiting for ${url}`);
}

const child = spawn(chrome, [
  "--headless=new", "--disable-gpu", "--hide-scrollbars",
  "--remote-debugging-port=9334", `--user-data-dir=${profile}`,
  "--window-size=1920,900", baseUrl,
], { stdio: "ignore" });

async function run() {
  const tabs = await waitJson("http://127.0.0.1:9334/json/list");
  const page = tabs.find((entry) => entry.type === "page" && entry.url.startsWith(baseUrl));
  if (!page) throw new Error("Live device tab was not created");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, { once: true });
    ws.addEventListener("error", reject, { once: true });
  });
  let nextId = 1;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (!message.id || !pending.has(message.id)) return;
    const promise = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) promise.reject(new Error(message.error.message)); else promise.resolve(message.result);
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async (expression) => {
    const response = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (response.exceptionDetails) throw new Error(response.exceptionDetails.text || "Browser evaluation failed");
    return response.result.value;
  };
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 900, deviceScaleFactor: 1, mobile: false });
  await delay(5000);
  const tabState = await evaluate(`(async () => { for(let n=0;n<100&&!window.elmaDesignerReady;n++)await new Promise(r=>setTimeout(r,250)); if(!window.elmaDesignerReady)throw new Error('Designer did not initialize'); await window.elmaDesignerReady; try{Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});}catch{} const button=document.querySelector('.tab-button[data-tab="logics"]'); const initial={hidden:button?.hidden,disabled:button?.disabled}; button?.click(); return {...initial,button:!!button, selected:button?.getAttribute('aria-selected'), panel:document.querySelector('#tab-logics')?.className}; })()`);
  console.log(JSON.stringify(tabState));
  await evaluate(`(async()=>{for(let n=0;n<80&&!window.elmaLogicsTab;n++)await new Promise(r=>setTimeout(r,250));if(!window.elmaLogicsTab)throw new Error('Logics controller did not initialize');await window.elmaLogicsTab.load();return true;})()`);
  await delay(3500);
  console.log(JSON.stringify(await evaluate(`({nodes:window.elmaLogicsTab?.editor?.graph?.nodes?.length,groups:window.elmaLogicsTab?.editor?.graph?.groups?.length,dom:document.querySelectorAll('#tab-logics .logic-group').length,status:document.querySelector('#tab-logics [data-logic-status]')?.textContent})`)));

  for (const locale of ["en", "ru"]) {
    await evaluate(`(() => { window.ElmaFirmwareI18n?.setLanguage(${JSON.stringify(locale)}); if(${JSON.stringify(locale)}==='ru'){const names={'cpu-temperature':'Температура чипа (°C)','above-50':'Выше 50 °C','beep-every-5s':'Сигнал каждые 5 секунд','buzzer-beep':'Зуммер №2 · Воспроизвести'};for(const node of window.elmaLogicsTab.editor.graph.nodes)node.name=names[node.id]||node.name;window.elmaLogicsTab.editor.graph.groups[0].name='Температура CPU выше 50 °C — зуммер';} window.elmaLogicsTab.canvas.render(); document.querySelector('#tab-logics .logic-group')?.scrollIntoView({block:'center',inline:'center'}); })()`);
    await delay(1200);
    const rect = await evaluate(`(() => {
      const node = document.querySelector('#tab-logics .logic-group');
      if (!node) throw new Error('Logic group is missing');
      const r = node.getBoundingClientRect();
      return { x: Math.max(0, r.x + scrollX - 12), y: Math.max(0, r.y + scrollY - 12), width: r.width + 24, height: r.height + 24, scale: 1 };
    })()`);
    const shot = await send("Page.captureScreenshot", { format: "png", clip: rect, captureBeyondViewport: true });
    const directory = path.join(outputRoot, locale);
    fs.mkdirSync(directory, { recursive: true });
    fs.writeFileSync(path.join(directory, "cpu-temperature-buzzer.png"), Buffer.from(shot.data, "base64"));
  }
  ws.close();
}

run().finally(async () => {
  child.kill();
  fixtureServer?.close();
  await delay(300);
  fs.rmSync(profile, { recursive: true, force: true });
}).catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
