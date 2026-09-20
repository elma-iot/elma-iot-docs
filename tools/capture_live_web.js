#!/usr/bin/env node
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const baseUrl = process.argv[2];
const outputDir = process.argv[3];
if (!baseUrl || !outputDir) {
  console.error("Usage: node capture_live_web.js <device-url> <output-dir>");
  process.exit(2);
}

const chrome = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const profile = path.join(process.env.TEMP || ".", `elma-doc-capture-${process.pid}`);
fs.mkdirSync(outputDir, { recursive: true });

const child = spawn(chrome, [
  "--headless=new",
  "--disable-gpu",
  "--hide-scrollbars",
  "--remote-debugging-port=9333",
  `--user-data-dir=${profile}`,
  "--window-size=1440,1200",
  baseUrl,
], { stdio: "ignore" });

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function waitJson(url) {
  for (let i = 0; i < 50; i += 1) {
    try { return await (await fetch(url)).json(); } catch { await delay(200); }
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function run() {
  const tabs = await waitJson("http://127.0.0.1:9333/json/list");
  const tab = tabs.find((item) => item.type === "page" && item.url.startsWith(baseUrl));
  if (!tab) throw new Error("Live device tab was not created");
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, { once: true });
    ws.addEventListener("error", reject, { once: true });
  });
  let nextId = 1;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message)); else resolve(message.result);
    }
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1200, deviceScaleFactor: 1, mobile: false });
  await delay(5000);

  async function capture(tabName, fileName) {
    await send("Runtime.evaluate", {
      expression: `document.querySelector('.tab-button[data-tab="${tabName}"]')?.click(); window.scrollTo(0,0);`,
      awaitPromise: true,
    });
    await delay(1500);
    const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    fs.writeFileSync(path.join(outputDir, fileName), Buffer.from(shot.data, "base64"));
  }

  await capture("gpio", "configuration.png");
  await capture("logics", "logics.png");
  await capture("hardware", "hardware-monitor.png");
  await capture("storage-internal", "internal-storage.png");
  ws.close();
}

run().finally(async () => {
  child.kill();
  await delay(300);
  fs.rmSync(profile, { recursive: true, force: true });
}).catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
