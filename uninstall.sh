#!/usr/bin/env bash
# Undo install.sh: remove only what it added to ~/.claude.
#
# Usage: ./uninstall.sh [--dry-run]
#
# Removes links in <claude home>/skills, agents and hooks that point into the core or a pack
# listed in <claude home>/workflow-packs. Anything else there (your own skills, a link to
# somewhere else) is left alone, and so are skills-backup/ and agents-backup/.
# CLAUDE_HOME overrides ~/.claude (used by the tests).
set -euo pipefail

core="$(cd "$(dirname "$0")" && pwd)"
home="${CLAUDE_HOME:-$HOME/.claude}"
dry=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) dry=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

sources=("$core")
if [ -f "$home/workflow-packs" ]; then
  while IFS= read -r p; do [ -n "$p" ] && sources+=("$p"); done < "$home/workflow-packs"
fi

ours() {
  local target s
  target="$(readlink "$1")"
  for s in "${sources[@]}"; do
    case "$target" in "$s"/*) return 0 ;; esac
  done
  return 1
}

for dir in skills agents hooks; do
  [ -d "$home/$dir" ] || continue
  while IFS= read -r l; do
    ours "$l" || continue
    if [ "$dry" = 1 ]; then
      echo "would remove $l"
    else
      rm "$l"
      echo "removed   $l"
    fi
  done < <(find "$home/$dir" -type l)
done

if [ -f "$home/workflow-hooks.json" ]; then
  if [ "$dry" = 1 ]; then
    python3 "$core/scripts/hooks.py" --home "$home" --dry-run --remove-all
  else
    python3 "$core/scripts/hooks.py" --home "$home" --remove-all
  fi
fi

import_line="@$core/preferences.md"
if [ -f "$home/CLAUDE.md" ] && grep -qxF "$import_line" "$home/CLAUDE.md"; then
  if [ "$dry" = 1 ]; then
    echo "would remove $import_line from $home/CLAUDE.md"
  else
    python3 -c 'import sys; p, line = sys.argv[1:]; t = open(p).read().split("\n"); open(p, "w").write("\n".join(l for l in t if l != line))' "$home/CLAUDE.md" "$import_line"
    echo "removed   $import_line from $home/CLAUDE.md"
  fi
fi

for f in workflow-core.json workflow-packs workflow-hooks.json; do
  [ -f "$home/$f" ] || continue
  if [ "$dry" = 1 ]; then
    echo "would remove $home/$f"
  else
    rm "$home/$f"
    echo "removed   $home/$f"
  fi
done

for b in skills-backup agents-backup; do
  [ -d "$home/$b" ] && echo "kept      $home/$b (what install.sh --backup moved aside; move it back by hand if you want it)"
done
echo "Repositories keep their own .claude/workflow.json, verification skill and run data. Delete those by hand if you no longer want them."
