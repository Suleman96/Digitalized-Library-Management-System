#!/usr/bin/env node
/**
 * stop-dev.mjs — stop every Iqra dev server.
 *
 * `npm run dev` starts uvicorn with --reload, which supervises its worker in a
 * separate process spawned through multiprocessing. That worker's command line
 * contains no mention of "uvicorn", so killing by name misses it, and killing
 * only the port owner lets the supervisor immediately respawn a replacement —
 * which then serves stale code from whenever *it* started.
 *
 * This walks the ports instead, and keeps going until nothing is listening.
 *
 *     npm run stop
 */

import { execSync } from "node:child_process";

const PORTS = [3000, 8000];
const MAX_PASSES = 8;
const isWindows = process.platform === "win32";

function run(command) {
  try {
    return execSync(command, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
  } catch {
    return "";
  }
}

/** PIDs currently listening on the given port. */
function listenersOn(port) {
  const pids = new Set();

  if (isWindows) {
    for (const line of run(`netstat -ano -p TCP`).split("\n")) {
      if (!line.includes("LISTENING")) continue;
      if (!new RegExp(`[:.]${port}\\s`).test(line)) continue;
      const pid = line.trim().split(/\s+/).pop();
      if (pid && pid !== "0") pids.add(pid);
    }
  } else {
    for (const pid of run(`lsof -ti tcp:${port} -sTCP:LISTEN`).split("\n")) {
      if (pid.trim()) pids.add(pid.trim());
    }
  }

  return [...pids];
}

function kill(pid) {
  run(isWindows ? `taskkill /PID ${pid} /T /F` : `kill -9 ${pid}`);
}

let killed = 0;

for (let pass = 1; pass <= MAX_PASSES; pass++) {
  const found = PORTS.flatMap((port) =>
    listenersOn(port).map((pid) => ({ port, pid })),
  );

  if (found.length === 0) {
    console.log(
      killed > 0
        ? `Stopped ${killed} process${killed === 1 ? "" : "es"}. Ports ${PORTS.join(" and ")} are free.`
        : `Nothing was running on ports ${PORTS.join(" or ")}.`,
    );
    process.exit(0);
  }

  for (const { port, pid } of found) {
    console.log(`  killing pid ${pid} on :${port}`);
    kill(pid);
    killed += 1;
  }

  // Give a supervisor a moment to respawn, so the next pass catches it.
  execSync(isWindows ? "ping -n 2 127.0.0.1 > NUL" : "sleep 1", { stdio: "ignore" });
}

console.error(
  `Ports ${PORTS.join(", ")} are still in use after ${MAX_PASSES} passes. ` +
    `Something is respawning; check for a stray supervisor process.`,
);
process.exit(1);
