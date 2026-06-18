import fs from "node:fs/promises";
import path from "node:path";

const CDP_BASE = "http://127.0.0.1:9223";
const APP_BASE = "http://127.0.0.1:5173";
const API_BASE = "http://127.0.0.1:5000";
const OUTPUT_DIR = path.resolve(
  "Final Year Project by Codex",
  "report_assets",
  "screenshots"
);
const ADMIN_TOKEN = "report-demo-admin-2026";
const SESSION_KEY = "diaspora-vote-session";
const RECEIPT_KEY = "diaspora-vote-receipt";
const ADMIN_SESSION_KEY = "prototype-registry-admin-token";

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
        if (!pending) {
          return;
        }
        this.pending.delete(message.id);
        if (message.error) {
          pending.reject(new Error(message.error.message));
        } else {
          pending.resolve(message.result);
        }
        return;
      }

      const waiters = this.eventWaiters.get(message.method) || [];
      this.eventWaiters.delete(message.method);
      for (const waiter of waiters) {
        waiter(message.params);
      }
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
      const timer = setTimeout(() => {
        reject(new Error(`Timed out waiting for ${method}`));
      }, timeoutMilliseconds);
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

async function api(pathname, options = {}) {
  const response = await fetch(`${API_BASE}${pathname}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `${pathname} failed`);
  }
  return payload;
}

async function main() {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  const adminHeaders = { "X-Admin-Token": ADMIN_TOKEN };
  const existingRegistry = await api("/admin/voters", {
    headers: adminHeaders,
  });
  for (const voter of existingRegistry.voters || []) {
    if (voter.display_name === "Report Demo Voter") {
      await api(`/admin/voters/${voter.id}`, {
        method: "DELETE",
        headers: adminHeaders,
      });
    }
  }
  await api("/admin/reset-demo-data", {
    method: "POST",
    headers: adminHeaders,
    body: JSON.stringify({
      confirmation_text: "RESET DEMO DATA",
      clear_registry: false,
    }),
  });

  const targets = await fetch(`${CDP_BASE}/json/list`).then((response) =>
    response.json()
  );
  const target = targets.find((item) => item.type === "page");
  if (!target) {
    throw new Error("No Chrome page target is available");
  }

  const client = new CdpClient(target.webSocketDebuggerUrl);
  await client.connect();
  await client.send("Page.enable");
  await client.send("Runtime.enable");
  await client.send("Network.enable");
  await client.send("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 1050,
    deviceScaleFactor: 1,
    mobile: false,
  });

  async function evaluate(expression, awaitPromise = true) {
    const result = await client.send("Runtime.evaluate", {
      expression,
      awaitPromise,
      returnByValue: true,
    });
    if (result.exceptionDetails) {
      throw new Error(
        result.exceptionDetails.exception?.description ||
          result.exceptionDetails.text ||
          "Page evaluation failed"
      );
    }
    return result.result?.value;
  }

  async function navigate(route) {
    const loaded = client.waitForEvent("Page.loadEventFired");
    await client.send("Page.navigate", { url: `${APP_BASE}${route}` });
    await loaded;
    await delay(1100);
    await evaluate("window.scrollTo(0, 0)");
  }

  async function spaNavigate(route) {
    await evaluate(`(() => {
      history.pushState({}, "", ${JSON.stringify(route)});
      window.dispatchEvent(new PopStateEvent("popstate"));
    })()`);
    await delay(1100);
    await evaluate("window.scrollTo(0, 0)");
  }

  async function reload() {
    const loaded = client.waitForEvent("Page.loadEventFired");
    await evaluate("location.reload()");
    await loaded;
    await delay(1100);
    await evaluate("window.scrollTo(0, 0)");
  }

  async function waitFor(expression, timeoutMilliseconds = 20000) {
    const startedAt = Date.now();
    while (Date.now() - startedAt < timeoutMilliseconds) {
      if (await evaluate(`Boolean(${expression})`)) {
        return;
      }
      await delay(250);
    }
    throw new Error(`Timed out waiting for: ${expression}`);
  }

  async function clickButton(label) {
    const clicked = await evaluate(`(() => {
      const button = [...document.querySelectorAll("button, a")]
        .find((item) => item.textContent.replace(/\\s+/g, " ").trim().includes(${JSON.stringify(label)}));
      if (!button) return false;
      button.click();
      return true;
    })()`);
    if (!clicked) {
      throw new Error(`Could not find control containing: ${label}`);
    }
  }

  async function fill(selector, value) {
    const changed = await evaluate(`(() => {
      const input = document.querySelector(${JSON.stringify(selector)});
      if (!input) return false;
      const setter = Object.getOwnPropertyDescriptor(
        HTMLInputElement.prototype,
        "value"
      ).set;
      setter.call(input, ${JSON.stringify(value)});
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    })()`);
    if (!changed) {
      throw new Error(`Could not fill ${selector}`);
    }
  }

  async function screenshot(filename) {
    await delay(350);
    const capture = await client.send("Page.captureScreenshot", {
      format: "png",
      fromSurface: true,
      captureBeyondViewport: false,
    });
    await fs.writeFile(
      path.join(OUTPUT_DIR, filename),
      Buffer.from(capture.data, "base64")
    );
    console.log(filename);
  }

  await navigate("/");
  await evaluate(
    `sessionStorage.removeItem(${JSON.stringify(SESSION_KEY)});
     sessionStorage.removeItem(${JSON.stringify(RECEIPT_KEY)});
     sessionStorage.removeItem(${JSON.stringify(ADMIN_SESSION_KEY)});`
  );
  await navigate("/");
  await screenshot("figure_4_1_landing_page.png");

  await spaNavigate("/login");
  await waitFor('document.body.innerText.includes("Voter Accreditation")');
  await screenshot("figure_4_2_accreditation_page.png");

  const authentication = await api("/login", {
    method: "POST",
    body: JSON.stringify({ nin: "12345678901" }),
  });
  const sessionInstanceId = crypto.randomUUID();
  const baseSession = {
    token: authentication.token,
    profile: {
      displayName: authentication.profile.display_name,
      diasporaLocation: authentication.profile.diaspora_location,
      voterCategory: authentication.profile.voter_category,
    },
    biometric: {
      verificationMode: authentication.biometric.verification_mode,
      fallbackMessage: authentication.biometric.fallback_message,
    },
    fallbackMessage: authentication.fallback_message,
    sessionInstanceId,
    eligibilityConfirmed: true,
    biometricVerified: false,
    selectedEvent: null,
  };
  await evaluate(
    `sessionStorage.setItem(${JSON.stringify(SESSION_KEY)}, ${JSON.stringify(
      JSON.stringify(baseSession)
    )})`
  );

  await navigate("/camera");
  await screenshot("figure_4_3_camera_verification_page.png");

  await api("/biometric-verify", {
    method: "POST",
    headers: { Authorization: `Bearer ${authentication.token}` },
    body: JSON.stringify({
      camera_capture: true,
      detection_mode: "report-evidence-session",
    }),
  });
  const verifiedSession = {
    ...baseSession,
    biometricVerified: true,
    detectionMode: "camera-frame-capture-fallback",
  };
  await evaluate(
    `sessionStorage.setItem(${JSON.stringify(SESSION_KEY)}, ${JSON.stringify(
      JSON.stringify(verifiedSession)
    )})`
  );

  await navigate("/dashboard");
  await waitFor('document.body.innerText.includes("Diaspora Voting Referendum")');
  await screenshot("figure_4_4_event_dashboard.png");

  const eventCatalog = await api("/events");
  const activeEvent = eventCatalog.events.find(
    (event) => event.event_id === eventCatalog.active_event_id
  );
  const ballotSession = { ...verifiedSession, selectedEvent: activeEvent };
  await evaluate(
    `sessionStorage.setItem(${JSON.stringify(SESSION_KEY)}, ${JSON.stringify(
      JSON.stringify(ballotSession)
    )})`
  );

  await navigate("/ballot");
  await screenshot("figure_4_5_ballot_page.png");
  await clickButton("Yes");
  await clickButton("Review Selection");
  await waitFor('document.body.innerText.includes("Review & Confirm Vote")');
  await screenshot("figure_4_6_vote_review_page.png");

  await clickButton("Generate Proof & Submit Vote");
  await waitFor(
    'location.pathname === "/receipt" && document.body.innerText.includes("Cryptographic Vote Receipt")',
    30000
  );
  await screenshot("figure_4_7_receipt_page.png");
  const receipt = JSON.parse(
    await evaluate(
      `sessionStorage.getItem(${JSON.stringify(RECEIPT_KEY)})`
    )
  );

  await spaNavigate("/board");
  await waitFor('document.body.innerText.includes("Published Ballots")');
  await waitFor(
    `document.body.innerText.includes(${JSON.stringify(receipt.ballotId)})`
  );
  await fill(
    'input[aria-label="Verify receipt by ballot ID"]',
    receipt.ballotId
  );
  await delay(250);
  await screenshot("figure_4_8_public_verification_board.png");
  await clickButton("Verify Receipt");
  await waitFor('document.querySelector(".verification-result")');
  await evaluate(
    'document.querySelector(".verification-card").scrollIntoView({block:"start"})'
  );
  await delay(300);
  await screenshot("figure_4_9_proof_verification_result.png");

  await spaNavigate("/tally");
  await waitFor('document.body.innerText.includes("Tally Dashboard")');
  await delay(800);
  await screenshot("figure_4_10_tally_dashboard.png");

  await evaluate(
    `sessionStorage.removeItem(${JSON.stringify(ADMIN_SESSION_KEY)})`
  );
  await navigate("/admin");
  await screenshot("figure_4_11_admin_login.png");

  await evaluate(
    `sessionStorage.setItem(${JSON.stringify(
      ADMIN_SESSION_KEY
    )}, ${JSON.stringify(ADMIN_TOKEN)})`
  );
  await reload();
  await waitFor('document.body.innerText.includes("Mock eligible voters")');
  await delay(500);
  await screenshot("figure_4_12_admin_registry.png");

  await fill('input[placeholder="11-digit mock NIN"]', "56789012345");
  await fill('input[placeholder="Example: Ifeoma Nwosu"]', "Report Demo Voter");
  await fill(
    'input[placeholder="Example: Dublin, Ireland"]',
    "Paris, France"
  );
  await clickButton("Create Mock Voter");
  await waitFor(
    'document.body.innerText.includes("Mock eligible voter created.")'
  );
  await evaluate("window.scrollTo(0, 0)");
  await screenshot("figure_4_13_admin_create_voter.png");

  client.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
