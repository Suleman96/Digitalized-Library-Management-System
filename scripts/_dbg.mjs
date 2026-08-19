import puppeteer from "puppeteer-core";
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox","--disable-gpu"] });
const page = await browser.newPage();
page.on("pageerror", e => console.log("PAGEERROR:", e.message.slice(0,200)));
page.on("console", m => { const t=m.text(); if (m.type()==="error" && !t.includes("403") && !t.includes("WebSocket")) console.log("CONSOLE:", t.slice(0,200)); });
await page.goto("http://127.0.0.1:3000/", { waitUntil: "networkidle2", timeout: 40000 });
await new Promise(r => setTimeout(r, 4000));

// Pure client-side interaction: clicking a prompt chip sets React state.
const before = await page.evaluate(() => document.querySelector('input[type="search"]')?.value ?? "(none)");
const clicked = await page.evaluate(() => {
  const btns = [...document.querySelectorAll("button")];
  const chip = btns.find(b => b.textContent.includes("gripping mystery"));
  if (!chip) return "chip not found";
  chip.click();
  return "clicked";
});
await new Promise(r => setTimeout(r, 2500));
const after = await page.evaluate(() => document.querySelector('input[type="search"]')?.value ?? "(none)");
console.log("chip:", clicked);
console.log("input before:", JSON.stringify(before));
console.log("input after :", JSON.stringify(after));
console.log("HYDRATED:", before !== after ? "YES - React state updated" : "NO - page is inert");
await browser.close();
