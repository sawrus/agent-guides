#!/usr/bin/env node

const { spawnSync } = require('node:child_process');
const path = require('node:path');

const scriptPath = path.resolve(__dirname, '..', 'agentic');
const args = process.argv.slice(2);

const result = spawnSync('bash', [scriptPath, ...args], {
  stdio: 'inherit',
  env: process.env,
});

if (result.error) {
  if (result.error.code === 'ENOENT') {
    console.error('[agentic][error] bash is required to run the agentic CLI from npx.');
    process.exit(127);
  }

  console.error(`[agentic][error] failed to launch CLI: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
