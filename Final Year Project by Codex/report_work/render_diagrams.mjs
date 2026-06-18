import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const CDP_BASE = "http://127.0.0.1:9223";
const DIAGRAM_DIR = path.resolve(
  "Final Year Project by Codex",
  "report_assets",
  "diagrams"
);
const NAMES = [
  "system_architecture",
  "voting_workflow",
  "use_case_diagram",
  "database_er_diagram",
  "zk_stark_verification_flow",
];

const delay = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

class CdpClient {
  constructor(webSocketUrl) {
    this.nextId = 1;
    this.pending = new Map();
    this.eventWaiters = new Map();
    this.socket = new WebSocket(webSocketUrl);
  }

  async connect() {
    await new Promise((resolve, reject) => {
      this.socket.addEventListener("open", resolve, { once: true });
      this.socket.addEventListener("error", reject, { once: true });
    });
    this.socket.addEventListener("message", (event) => {
      const message = JSON.parse(String(event.data));
      if (message.id) {
        const pending = this.pending.get(message.id);
        if (!pending) return;
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(message.error.message));
        else pending.resolve(message.result);
        return;
      }
      const waiters = this.eventWaiters.get(message.method) || [];
      this.eventWaiters.delete(message.method);
      for (const waiter of waiters) waiter(message.params);
    });
  }

  send(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  waitForEvent(method, timeoutMilliseconds = 15000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(
        () => reject(new Error(`Timed out waiting for ${method}`)),
        timeoutMilliseconds
      );
      const waiters = this.eventWaiters.get(method) || [];
      waiters.push((params) => {
        clearTimeout(timer);
        resolve(params);
      });
      this.eventWaiters.set(method, waiters);
    });
  }

  close() {
    this.socket.close();
  }
}

async function main() {
  const targets = await fetch(`${CDP_BASE}/json/list`).then((response) =>
    response.json()
  );
  const target = targets.find((item) => item.type === "page");
  if (!target) throw new Error("No Chrome page target is available");

  const client = new CdpClient(target.webSocketDebuggerUrl);
  await client.connect();
  await client.send("Page.enable");
  await client.send("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false,
  });

  for (const name of NAMES) {
    const source = path.join(DIAGRAM_DIR, `${name}.svg`);
    const loaded = client.waitForEvent("Page.loadEventFired");
    await client.send("Page.navigate", { url: pathToFileURL(source).href });
    await loaded;
    await delay(300);
    const screenshot = await client.send("Page.captureScreenshot", {
      format: "png",
      fromSurface: true,
      captureBeyondViewport: false,
    });
    await fs.writeFile(
      path.join(DIAGRAM_DIR, `${name}.png`),
      Buffer.from(screenshot.data, "base64")
    );
    console.log(`${name}.png`);
  }

  client.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
