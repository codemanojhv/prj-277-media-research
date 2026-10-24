import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
if (existsSync(path.join(root, ".env")) && typeof process.loadEnvFile === "function") {
  process.loadEnvFile(path.join(root, ".env"));
}
const apiDir = path.join(root, "apps", "api");
const webDir = path.join(root, "apps", "web");
const uv = process.platform === "win32" ? "uv.exe" : "uv";
const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const apiPort = process.env.API_PORT || "8000";
const webPort = process.env.WEB_PORT || "3000";
const apiUrl = `http://127.0.0.1:${apiPort}/api`;
const python = process.platform === "win32"
  ? path.join(apiDir, ".venv", "Scripts", "python.exe")
  : path.join(apiDir, ".venv", "bin", "python");

function setup(command, args, cwd, label) {
  console.log(`\n[DEMO] ${label}`);
  const isWindowsBatch = process.platform === "win32" && command === npm;
  const executable = isWindowsBatch ? (process.env.ComSpec || "cmd.exe") : command;
  const executableArgs = isWindowsBatch ? ["/d", "/s", "/c", `${command} ${args.join(" ")}`] : args;
  const result = spawnSync(executable, executableArgs, { cwd, stdio: "inherit", env: { ...process.env } });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${label} failed with exit code ${result.status}`);
}

function start(command, args, cwd, label, env = process.env) {
  const child = spawn(command, args, {
    cwd,
    stdio: "inherit",
    env,
    windowsHide: true,
  });
  child.on("error", (error) => {
    console.error(`[${label}] could not start: ${error.message}`);
    stopAll(1);
  });
  child.on("exit", (code, signal) => {
    if (!stopping) {
      console.log(`[DEMO] ${label} exited (${signal || code})`);
      stopAll(code || 0);
    }
  });
  children.push(child);
  return child;
}

const children = [];
let stopping = false;
function stopAll(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children) {
    if (child.exitCode === null) {
      if (process.platform === "win32" && child.pid) {
        spawnSync("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore" });
      } else {
        child.kill("SIGTERM");
      }
    }
  }
  setTimeout(() => process.exit(code), 800);
}

async function waitForApi(child) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (child.exitCode !== null) throw new Error("API stopped during startup");
    try {
      const response = await fetch(`${apiUrl}/health`);
      if (response.ok) return;
    } catch {
      // Give Uvicorn a moment to bind before the next health request.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("API did not become healthy within 30 seconds");
}

process.on("SIGINT", () => stopAll(0));
process.on("SIGTERM", () => stopAll(0));

try {
  setup(uv, ["sync", "--group", "dev"], apiDir, "Installing / checking local Python dependencies");
  setup(python, ["-m", "alembic", "upgrade", "head"], apiDir, "Applying SQLite migrations");
  setup(python, ["-m", "app.seed"], apiDir, "Loading synthetic demo data and running analysis + clustering");
  if (!existsSync(path.join(webDir, "node_modules"))) {
    setup(npm, ["install"], webDir, "Installing web dependencies");
  }

  const api = start(python, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", apiPort], apiDir, "API");
  await waitForApi(api);
  const nextCli = path.join(webDir, "node_modules", "next", "dist", "bin", "next");
  const web = start(process.execPath, [nextCli, "dev", "--hostname", "127.0.0.1", "--port", webPort], webDir, "Web app", {
    ...process.env,
    NEXT_PUBLIC_API_URL: apiUrl,
    NEXT_PUBLIC_LOCAL_REACTIONS: "1",
  });
  void web;
  console.log(`\nPRJ_277 demo is ready:\n  Research dashboard: http://127.0.0.1:${webPort}\n  API documentation: ${apiUrl.replace(/\/api$/, "/docs")}\n  Health: ${apiUrl}/health\n\nPress Ctrl+C to stop both services.`);
} catch (error) {
  console.error(`\n[DEMO] ${error.message}`);
  stopAll(1);
}
