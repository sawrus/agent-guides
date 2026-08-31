#!/usr/bin/env node
// Thin npm launcher for the self-contained agentic Rust binary.
// On first run it downloads the release asset matching this package version
// from GitHub Releases into a per-version cache, then executes it.

"use strict";

const { spawnSync, execFileSync } = require("node:child_process");
const fs = require("node:fs");
const https = require("node:https");
const os = require("node:os");
const path = require("node:path");

const REPO = "sawrus/agent-guides";
const VERSION = require("../package.json").version;

function fail(message) {
  console.error(`[agentic][error] ${message}`);
  process.exit(1);
}

function assetName() {
  const arch = { x64: "x86_64", arm64: "aarch64" }[process.arch];
  if (!arch) fail(`Unsupported architecture: ${process.arch}`);
  switch (process.platform) {
    case "linux":
      return `agentic-${arch}-unknown-linux-musl.tar.gz`;
    case "darwin":
      return `agentic-${arch}-apple-darwin.tar.gz`;
    case "win32":
      if (arch !== "x86_64") fail(`Unsupported Windows architecture: ${process.arch}`);
      return "agentic-x86_64-pc-windows-msvc.zip";
    default:
      fail(`Unsupported platform: ${process.platform}. Download a binary from https://github.com/${REPO}/releases`);
  }
}

function cacheDir() {
  const base =
    process.env.XDG_CACHE_HOME && process.env.XDG_CACHE_HOME !== ""
      ? process.env.XDG_CACHE_HOME
      : path.join(os.homedir(), ".cache");
  return path.join(base, "agentic-npm", VERSION);
}

function binaryPath() {
  const name = process.platform === "win32" ? "agentic.exe" : "agentic";
  return path.join(cacheDir(), name);
}

function download(url, dest, redirects = 0) {
  return new Promise((resolve, reject) => {
    if (redirects > 5) return reject(new Error(`Too many redirects for ${url}`));
    https
      .get(url, { headers: { "User-Agent": `agentic-npm/${VERSION}` } }, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          res.resume();
          return resolve(download(res.headers.location, dest, redirects + 1));
        }
        if (res.statusCode !== 200) {
          res.resume();
          return reject(new Error(`HTTP ${res.statusCode} for ${url}`));
        }
        const file = fs.createWriteStream(dest);
        res.pipe(file);
        file.on("finish", () => file.close(resolve));
        file.on("error", reject);
      })
      .on("error", reject);
  });
}

async function ensureBinary() {
  const binary = binaryPath();
  if (process.env.AGENTIC_NPM_BINARY) return process.env.AGENTIC_NPM_BINARY;
  if (fs.existsSync(binary)) return binary;

  const asset = assetName();
  const url = `https://github.com/${REPO}/releases/download/v${VERSION}/${asset}`;
  const dir = cacheDir();
  fs.mkdirSync(dir, { recursive: true });
  const archive = path.join(dir, asset);

  console.error(`[agentic] Downloading ${url}`);
  await download(url, archive);

  // tar handles both .tar.gz and .zip (bsdtar) on linux/macos/windows 10+.
  try {
    execFileSync("tar", ["-xf", archive, "-C", dir], { stdio: "inherit" });
  } catch (err) {
    fail(`Failed to extract ${archive}: ${err.message}`);
  }
  fs.rmSync(archive, { force: true });
  if (!fs.existsSync(binary)) fail(`Archive did not contain the agentic binary (${binary})`);
  if (process.platform !== "win32") fs.chmodSync(binary, 0o755);
  return binary;
}

ensureBinary()
  .then((binary) => {
    const result = spawnSync(binary, process.argv.slice(2), { stdio: "inherit" });
    if (result.error) fail(`Failed to launch ${binary}: ${result.error.message}`);
    process.exit(result.status === null ? 1 : result.status);
  })
  .catch((err) => fail(`${err.message}. You can install manually from https://github.com/${REPO}/releases`));
