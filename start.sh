#!/usr/bin/env bash
# Claude Code SDLC — start or continue the SDLC in a project from the terminal.
#
#   ./start.sh [PROJECT_DIR] [--step]
#
# 1. finds the Claude Code CLI (PATH, ~/.local/bin, or the copy bundled with the Claude desktop app);
# 2. installs the `sdlc` plugin from the GitHub marketplace itmax04/claude-code-sdlc, or updates it;
# 3. opens Claude Code in PROJECT_DIR with `/sdlc:run` (or `/sdlc:run step` with --step).
# Nothing is published and no settings outside Claude Code's own plugin registry are changed.
set -euo pipefail

MARKETPLACE_SRC="itmax04/claude-code-sdlc"
MARKETPLACE_NAME="claude-code-sdlc"
PLUGIN="sdlc@${MARKETPLACE_NAME}"

PROJECT="${1:-$PWD}"
ARG=""
[ "${2:-}" = "--step" ] && ARG=" step"
[ "${1:-}" = "--step" ] && { PROJECT="$PWD"; ARG=" step"; }

find_claude() {
  if command -v claude >/dev/null 2>&1; then command -v claude; return; fi
  if [ -x "$HOME/.local/bin/claude" ]; then echo "$HOME/.local/bin/claude"; return; fi
  local base="$HOME/Library/Application Support/Claude/claude-code"
  if [ -d "$base" ]; then
    local newest
    newest=$(ls -1 "$base" 2>/dev/null | sort -t. -k1,1n -k2,2n -k3,3n | tail -1)
    if [ -n "$newest" ]; then
      local bin
      bin=$(find "$base/$newest" -type f -path "*/MacOS/claude" 2>/dev/null | head -1)
      [ -n "$bin" ] && { echo "$bin"; return; }
    fi
  fi
}

CLAUDE="$(find_claude || true)"
if [ -z "$CLAUDE" ]; then
  echo "Claude Code CLI не найден. Установите его (одна команда) и запустите start.sh снова:"
  echo "  curl -fsSL https://claude.ai/install.sh | bash"
  echo "Или откройте проект в приложении Claude (вкладка Code) и наберите: /sdlc:run"
  exit 1
fi

if [ ! -d "$PROJECT/.git" ] && ! git -C "$PROJECT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Папка проекта не является git-репозиторием: $PROJECT"
  exit 1
fi

if "$CLAUDE" plugin list --json 2>/dev/null | grep -q "\"${PLUGIN}\""; then
  "$CLAUDE" plugin marketplace update "$MARKETPLACE_NAME" >/dev/null 2>&1 || true
  "$CLAUDE" plugin update "$PLUGIN" >/dev/null 2>&1 || true
else
  echo "Устанавливаю плагин ${PLUGIN} из ${MARKETPLACE_SRC}…"
  if ! "$CLAUDE" plugin install sdlc --marketplace "$MARKETPLACE_SRC" --scope user -y; then
    echo "Не удалось установить плагин. Если репозиторий приватный, выполните «gh auth setup-git» и повторите."
    exit 1
  fi
fi

cd "$PROJECT"
exec "$CLAUDE" "/sdlc:run${ARG}"
