#!/usr/bin/env node
"use strict";

// npm postinstall hook: install the generic skill to ~/.agent/skills/checkpoint
// unless it already exists. Mirrors agent-checkpoint skill-install --global
// without invoking the Python wrapper, which may not be on PATH during install.

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const destination = path.join(os.homedir(), ".agent", "skills", "checkpoint");
if (fs.existsSync(destination)) {
  process.exit(0);
}

const launcher = path.join(__dirname, "agent-checkpoint.cjs");
const result = spawnSync(
  process.execPath,
  [launcher, "skill-install", "--global"],
  { stdio: "inherit" }
);
process.exit(result.status === null ? 1 : result.status);
