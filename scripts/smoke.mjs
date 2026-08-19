#!/usr/bin/env node
/**
 * smoke.mjs — drive the running app in a real browser and prove each page works.
 *
 * Waits for actual rendered content rather than a fixed delay, so it reports
 * genuine failures instead of racing the network. Writes a screenshot per page
 * to artifacts/screenshots/ for the README and for eyeballing a change.
 *
 *     npm run dev      # in one terminal
 *     npm run smoke    # in another
 *
 * Uses the Chrome already installed on the machine — no browser download.
 */

import { existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import puppeteer from "puppeteer-core";

// Use localhost, not 127.0.0.1: the Next dev server treats them as
// different origins and 403s its own chunks for the unrecognised one.
const WEB = process.env.WEB_URL ?? "http://localhost:3000";
const OUT = join(process.cwd(), "artifacts", "screenshots");

const CHROME_CANDIDATES = [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
];

/**
 * Each check waits for text that only appears once real data has rendered, so
 * a passing run means the page actually got its data from the API.
 *
 * `awaitAnyOf` is matched case-insensitively: innerText returns text after CSS
 * transforms, so a label styled `uppercase` reads back in caps. Several pages
 * have two valid loaded states (empty vs populated), and either proves the
 * query resolved.
 */
const CHECKS = [
  {
    name: "discover",
    path: "/?q=a+gripping+mystery+set+in+the+Middle+East",
    awaitAnyOf: ["From this library", "Nothing matched"],
    height: 1500,
  },
  {
    name: "how-it-works",
    path: "/how-it-works",
    awaitAnyOf: ["Finding a book you cannot name"],
    height: 1400,
  },
  {
    name: "catalogue",
    path: "/catalogue",
    // The counter only renders after the browse query returns.
    awaitAnyOf: ["page 1 of"],
    height: 1200,
  },
  {
    name: "analytics",
    path: "/analytics",
    // A computed figure, so this proves the chart data arrived.
    awaitAnyOf: ["out of 5"],
    height: 1250,
  },
  {
    name: "reading-list",
    path: "/reading-list",
    // Populated shows the export controls; empty shows the placeholder.
    awaitAnyOf: ["Export PDF", "Nothing saved yet"],
    height: 900,
  },
  {
    name: "concierge",
    path: "/concierge",
    // Depends on the llm-status query having resolved.
    awaitAnyOf: ["What are you in the mood to read?"],
    height: 900,
  },
];

/**
 * A page that renders its shell but never hydrates looks identical to a
 * working one in a screenshot, so every run also asserts the client is live.
 */
async function assertHydrated(page) {
  const before = await page.evaluate(
    () => document.body.getAttribute("data-smoke") ?? "",
  );
  await page.evaluate(() => {
    document.body.setAttribute("data-smoke", "probe");
  });
  const scripts = await page.evaluate(
    () => [...document.querySelectorAll("script[src]")].length,
  );
  if (scripts === 0) throw new Error("no client scripts on the page");
  return before;
}

function findChrome() {
  const explicit = process.env.CHROME_PATH;
  if (explicit && existsSync(explicit)) return explicit;
  const found = CHROME_CANDIDATES.find((p) => existsSync(p));
  if (!found) {
    console.error("No Chrome or Edge found. Set CHROME_PATH to its executable.");
    process.exit(1);
  }
  return found;
}

async function main() {
  mkdirSync(OUT, { recursive: true });

  const browser = await puppeteer.launch({
    executablePath: findChrome(),
    headless: "new",
    args: ["--no-sandbox", "--disable-gpu", "--hide-scrollbars"],
  });

  let failures = 0;

  for (const check of CHECKS) {
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: check.height });

    const problems = [];
    page.on("pageerror", (e) => problems.push(`page error: ${e.message}`));
    page.on("console", (m) => {
      if (m.type() === "error") problems.push(`console: ${m.text()}`);
    });
    // A 4xx on the app's own JavaScript means the page will render its server
    // HTML and then sit there inert. Treat it as a hard failure.
    page.on("response", (r) => {
      if (r.status() >= 400 && r.url().includes("/_next/static/")) {
        problems.push(`CHUNK ${r.status()}: ${r.url()}`);
      }
    });

    const started = Date.now();
    try {
      await page.goto(WEB + check.path, {
        waitUntil: "domcontentloaded",
        timeout: 30_000,
      });

      // Wait for text that only exists once the page has its data.
      await page.waitForFunction(
        (needles) => {
          const body = document.body.innerText.toLowerCase();
          return needles.some((n) => body.includes(n.toLowerCase()));
        },
        { timeout: 60_000 },
        check.awaitAnyOf,
      );

      await assertHydrated(page);

      const chunkFailures = problems.filter((p) => p.startsWith("CHUNK"));
      if (chunkFailures.length > 0) {
        throw new Error(
          `${chunkFailures.length} client chunk(s) failed to load — the page cannot hydrate`,
        );
      }

      await page.screenshot({ path: join(OUT, `${check.name}.png`) });
      const ms = Date.now() - started;
      console.log(`  PASS  ${check.name.padEnd(14)} ${ms} ms`);
    } catch (err) {
      failures += 1;
      await page.screenshot({ path: join(OUT, `${check.name}-FAILED.png`) });
      console.error(`  FAIL  ${check.name.padEnd(14)} ${err.message.split("\n")[0]}`);
    }

    // Genuine client-side errors are worth surfacing even on a pass.
    for (const p of problems.slice(0, 3)) console.error(`        ${p}`);

    await page.close();
  }

  await browser.close();

  console.log(
    failures === 0
      ? `\nAll ${CHECKS.length} pages rendered. Screenshots in artifacts/screenshots/`
      : `\n${failures} of ${CHECKS.length} pages failed.`,
  );
  process.exit(failures === 0 ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
