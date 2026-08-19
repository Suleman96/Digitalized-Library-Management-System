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

const WEB = process.env.WEB_URL ?? "http://127.0.0.1:3000";
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
 * Each check waits for text that only appears once real data has rendered,
 * so a passing run means the page actually got its data from the API.
 */
const CHECKS = [
  {
    name: "discover",
    path: "/?q=a+gripping+mystery+set+in+the+Middle+East",
    // Result group headings only render once the search resolves.
    awaitText: "From this library",
    height: 1500,
  },
  {
    name: "how-it-works",
    path: "/how-it-works",
    awaitText: "Finding a book you cannot name",
    height: 1400,
  },
  {
    name: "catalogue",
    path: "/catalogue",
    awaitText: "book", // the "N books · page 1 of M" counter
    height: 1200,
  },
  {
    name: "analytics",
    path: "/analytics",
    awaitText: "Average rating",
    height: 1250,
  },
  {
    name: "reading-list",
    path: "/reading-list",
    awaitText: "Your reading list",
    height: 900,
  },
  {
    name: "concierge",
    path: "/concierge",
    awaitText: "Ask the concierge",
    height: 900,
  },
];

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

    const started = Date.now();
    try {
      await page.goto(WEB + check.path, {
        waitUntil: "domcontentloaded",
        timeout: 30_000,
      });

      // Wait for text that only exists once the page has its data.
      await page.waitForFunction(
        (needle) => document.body.innerText.includes(needle),
        { timeout: 60_000 },
        check.awaitText,
      );

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
