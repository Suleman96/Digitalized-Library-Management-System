import puppeteer from "puppeteer-core";
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: "new", args: ["--no-sandbox","--disable-gpu"] });
const page = await browser.newPage();
page.on("console", m => { const t = m.text(); if (t.includes("hydrat") || t.includes("did not match") || t.includes("didn't match")) console.log("---\n" + t.slice(0, 1400)); });
await page.goto("http://localhost:3000/how-it-works", { waitUntil: "networkidle2", timeout: 40000 });
await new Promise(r => setTimeout(r, 5000));
await browser.close();
