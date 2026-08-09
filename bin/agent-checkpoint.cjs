#!/usr/bin/env node
"use strict";

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const launcher = path.join(root, "core", "bin", "agent-checkpoint");
const python = process.env.AGENT_CHECKPOINT_PYTHON || "python3";
const result = spawnSync(python, [launcher, ...process.argv.slice(2)], {
  stdio: "inherit",
});

if (result.error) {
  process.stderr.write("agent-checkpoint requires Python 3.11 or newer on PATH.\n");
  process.exit(127);
}
process.exit(result.status === null ? 1 : result.status);
