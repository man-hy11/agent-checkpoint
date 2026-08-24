#!/usr/bin/env node
"use strict";

// Manual skill-install helper: installs the generic skill to
// ~/.agent/skills/checkpoint unless it already exists. Mirrors
// agent-checkpoint skill-install --global without invoking the Python
// wrapper, which may not be on PATH during install.
//
// It also links the canonical skill into whichever supported agent
// directories are already present on this machine (~/.claude, ~/.codex,
// ~/.config/opencode).
//
// This is NOT wired to npm's postinstall lifecycle -- `npm install -g
// agent-checkpoint` only installs the CLI. Run this explicitly when you also
// want the skill links:
//
//   npm run install-skill
//
// (or, once the CLI is on PATH: agent-checkpoint skill-install --global).
// Prefer installing the skill itself via a Claude Code plugin or
// `npx skills add` instead -- see README.md.

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const destination = path.join(os.homedir(), ".agent", "skills", "checkpoint");
if (fs.existsSync(destination)) {
  process.exit(0);
}

// Detect which agents are actually installed on this machine by checking for
// their config directory, and only request links for those. Agents with no
// directory present are left alone -- run `agent-checkpoint skill-install`
// manually later if one is installed afterward.
const AGENT_DETECTORS = [
  { name: "claude-code", dir: path.join(os.homedir(), ".claude") },
  { name: "codex", dir: process.env.CODEX_HOME || path.join(os.homedir(), ".codex") },
  { name: "opencode", dir: path.join(os.homedir(), ".config", "opencode") },
];

const detectedAgents = AGENT_DETECTORS.filter(({ dir }) => {
  try {
    return fs.statSync(dir).isDirectory();
  } catch {
    return false;
  }
}).map(({ name }) => name);

const launcher = path.join(__dirname, "agent-checkpoint.cjs");
const args = [launcher, "skill-install", "--global"];
for (const name of detectedAgents) {
  args.push("--agent", name);
}

const result = spawnSync(process.execPath, args, { stdio: "inherit" });
process.exit(result.status === null ? 1 : result.status);
