#!/usr/bin/env bash
# check-agent-setup.sh
#
# Pull-based agent standards setup.
# Runs when Claude Code starts (via SessionStart hook) and ensures each repo has
# AGENTS.md, a CLAUDE.md that imports it, and an AGENT.md redirect stub for Amp.
#
# Hook setup — add to ~/.claude/settings.json:
#
#   {
#     "hooks": {
#       "SessionStart": [
#         {
#           "matcher": "startup|resume",
#           "hooks": [{ "type": "command", "command": "/path/to/agent-patterns/scripts/check-agent-setup.sh" }]
#         }
#       ]
#     }
#   }

set -euo pipefail

GITHUB_RAW="${AGENT_PATTERNS_RAW_URL:-https://raw.githubusercontent.com/komplettsystem/agent-patterns/main/AGENT-BASE.md}"
# AGENTS.md is the primary per-project file (cross-tool standard: read natively by Codex
# CLI, Cursor, Copilot, etc). A small AGENT.md (singular) stub also gets created purely to
# redirect Amp, which reads that exact filename natively. See MULTI-AGENT-COMPAT.md.
STANDARDS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_FILE="$STANDARDS_DIR/AGENT-BASE.md"

# Resolve base content: prefer local, fall back to GitHub
get_base_content() {
  if [[ -f "$BASE_FILE" ]]; then
    cat "$BASE_FILE"
  elif command -v curl &>/dev/null; then
    curl -fsSL "$GITHUB_RAW"
  elif command -v wget &>/dev/null; then
    wget -qO- "$GITHUB_RAW"
  else
    echo "[agent-standards] ERROR: no local AGENT-BASE.md and no curl/wget available" >&2
    exit 1
  fi
}

# --- Inbox check (TRIAGE-LOOP.md, step 3) ---
# SessionStart hook stdout is added to the agent's context. The inbox lives in
# Slack, which only the agent can reach (via its connector), so the hook hands
# the agent an instruction instead of reading the channel itself.
# Opt-in: set INBOX_CHANNEL_NAME and INBOX_CHANNEL_ID in the environment, or in
# inbox.local.conf at this repo's root (gitignored, shell syntax).
INBOX_CONF="$STANDARDS_DIR/inbox.local.conf"
# shellcheck source=/dev/null
[[ -f "$INBOX_CONF" ]] && source "$INBOX_CONF"
if [[ -n "${INBOX_CHANNEL_NAME:-}" && -n "${INBOX_CHANNEL_ID:-}" ]]; then
cat << EOF
[inbox] Capture inbox: Slack #${INBOX_CHANNEL_NAME} (channel ID ${INBOX_CHANNEL_ID}). See agent-patterns/TRIAGE-LOOP.md.
Once, early in this session, without delaying or blocking the user's first request:
- Read the channel with the Slack connector. Messages with a white_check_mark reaction are already filed; skip them.
- Report in one line: open items, how many belong to the current repo, and any older than six weeks (bankruptcy candidates).
- Offer to file the current repo's items. Leave everything else untouched.
- Filing: follow the repo's own conventions; otherwise append a dated entry to log/YYYY-MM.md and rewrite STATUS.md if affected. Then add a white_check_mark reaction to the message.
- File only with the user in the session. If Slack is unreachable, say so; never report an unreadable inbox as empty.
EOF
fi

# --- Liveness check ---
# A harness fails by being abandoned, not by being wrong, so each session reports which
# tracked projects have let STATUS.md go stale. Opt-in like the inbox: set
# LIVENESS_PROJECTS (space-separated directory names under the projects root) in
# inbox.local.conf. LIVENESS_DAYS (default 14) and LIVENESS_ROOT (default: the parent of
# this repo) are optional. A missing STATUS.md counts as stale, never as fine.
if [[ -n "${LIVENESS_PROJECTS:-}" ]]; then
  LIVENESS_ROOT="${LIVENESS_ROOT:-$(dirname "$STANDARDS_DIR")}"
  LIVENESS_DAYS="${LIVENESS_DAYS:-14}"
  now="$(date +%s)"
  live=0
  total=0
  stale=""
  for project in $LIVENESS_PROJECTS; do
    total=$((total + 1))
    status_file="$LIVENESS_ROOT/$project/STATUS.md"
    if [[ ! -f "$status_file" ]]; then
      stale="$stale $project (no STATUS.md),"
      continue
    fi
    mtime="$(stat -c %Y "$status_file" 2>/dev/null || stat -f %m "$status_file")"
    age_days=$(( (now - mtime) / 86400 ))
    if (( age_days < LIVENESS_DAYS )); then
      live=$((live + 1))
    else
      stale="$stale $project (${age_days}d),"
    fi
  done
  echo "[liveness] $live of $total tracked projects have a STATUS.md updated in the last $LIVENESS_DAYS days."
  if [[ -n "$stale" ]]; then
    echo "Stale:${stale%,}"
  fi
  echo "Mention this in one line early in the session, without blocking the user's first request. Never refresh a STATUS.md just to move the number; only rewrite it when its content changed."
fi

# Only run inside a git repo
if ! git rev-parse --git-dir &>/dev/null 2>&1; then
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"

# Skip the standards repo itself
if [[ "$REPO_ROOT" == "$STANDARDS_DIR" ]]; then
  exit 0
fi

AGENTS_MD="$REPO_ROOT/AGENTS.md"
AGENT_MD="$REPO_ROOT/AGENT.md"
CLAUDE_MD="$REPO_ROOT/CLAUDE.md"
CHANGED=0

# --- AGENTS.md (primary) ---
if [[ ! -f "$AGENTS_MD" ]]; then
  get_base_content > "$AGENTS_MD"
  cat >> "$AGENTS_MD" << 'EOF'

---

## Project-Specific Guidelines

<!-- Project-specific rules, conventions, and stack context go here.
     The base guidelines above come from agent-patterns/AGENT-BASE.md.
     Do not edit the base section here — update AGENT-BASE.md instead. -->
EOF
  echo "[agent-standards] Created AGENTS.md in $REPO_ROOT" >&2
  CHANGED=1
fi

# --- AGENT.md (singular) — Amp-redirect stub only, see MULTI-AGENT-COMPAT.md ---
if [[ ! -f "$AGENT_MD" ]]; then
  cat > "$AGENT_MD" << 'EOF'
# This project's instructions live in AGENTS.md

You're reading this because you're Amp, which looks for `AGENT.md` natively. This
project's real instructions are in `AGENTS.md` — read that file now, it has everything.
EOF
  echo "[agent-standards] Created AGENT.md (Amp redirect stub) in $REPO_ROOT" >&2
  CHANGED=1
fi

# --- CLAUDE.md (Claude Code specific) ---
if [[ ! -f "$CLAUDE_MD" ]]; then
  echo "@AGENTS.md" > "$CLAUDE_MD"
  echo "[agent-standards] Created CLAUDE.md in $REPO_ROOT" >&2
  CHANGED=1
elif ! grep -qF "@AGENTS.md" "$CLAUDE_MD"; then
  # Prepend so base loads first; existing project content follows and takes precedence
  { printf '@AGENTS.md\n\n'; cat "$CLAUDE_MD"; } > "${CLAUDE_MD}.tmp" && mv "${CLAUDE_MD}.tmp" "$CLAUDE_MD"
  echo "[agent-standards] Prepended @AGENTS.md to existing CLAUDE.md in $REPO_ROOT" >&2
  CHANGED=1
fi

if [[ "$CHANGED" -eq 1 ]]; then
  echo "[agent-standards] Setup complete — review and commit the new files." >&2
fi
