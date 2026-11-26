#!/usr/bin/env bash
# Update the core and each installed pack, then relink with install.sh.
#
# Usage: ./update.sh [--dry-run]
#
# The core moves to its latest release tag (vX.Y.Z). If <claude home>/workflow-core.json says you
# own the core, it pulls your current branch instead (fast-forward only), because you work on main.
# A core with uncommitted changes to tracked files is left alone unless you own it.
# Each pack listed in <claude home>/workflow-packs that has an upstream branch is pulled
# (fast-forward only); a pack with no remote is skipped.
# install.sh then runs with every installed pack, so new skills, agents and hooks are linked and
# hook entries are brought in line with each hooks.json. Links into the core or a pack whose
# target no longer exists (a skill was removed or renamed) are removed.
# CLAUDE_HOME overrides ~/.claude (used by the tests).
set -euo pipefail

# One block, so bash has read all of it before checkout replaces this file.
{
core="$(cd "$(dirname "$0")" && pwd)"
home="${CLAUDE_HOME:-$HOME/.claude}"
dry=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) dry=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

owner=false
if [ -f "$home/workflow-core.json" ]; then
  owner="$(python3 -c 'import json,sys; print("true" if json.load(open(sys.argv[1])).get("owner") else "false")' "$home/workflow-core.json")"
fi

if [ "$owner" = true ]; then
  if [ "$dry" = 1 ]; then
    echo "would pull  $core (you own the core: fast-forward of the current branch)"
  else
    git -C "$core" pull --ff-only --quiet
    echo "pulled    $core ($(git -C "$core" rev-parse --abbrev-ref HEAD))"
  fi
else
  git -C "$core" fetch --tags --quiet
  latest="$(git -C "$core" tag -l 'v[0-9]*' --sort=-v:refname | head -n 1)"
  current="$(git -C "$core" describe --tags --exact-match 2>/dev/null || git -C "$core" rev-parse --short HEAD)"
  if [ -z "$latest" ]; then
    echo "no releases yet; core stays at $current"
  elif [ "$latest" = "$current" ]; then
    echo "ok        core is on the latest release, $latest"
  elif ! git -C "$core" diff --quiet HEAD; then
    echo "core has uncommitted changes; commit or discard them, then rerun (latest release: $latest)" >&2
    exit 1
  elif [ "$dry" = 1 ]; then
    echo "would move core from $current to $latest"
  else
    git -C "$core" -c advice.detachedHead=false checkout --quiet "$latest"
    echo "moved     core from $current to $latest"
  fi
fi

packs=()
if [ -f "$home/workflow-packs" ]; then
  while IFS= read -r p; do [ -n "$p" ] && [ -d "$p" ] && packs+=("$p"); done < "$home/workflow-packs"
fi
pack_args=()
for p in ${packs[@]+"${packs[@]}"}; do
  pack_args+=(--pack "$p")
  if ! git -C "$p" rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
    echo "skipped   $p (no upstream branch to pull from)"
  elif [ "$dry" = 1 ]; then
    echo "would pull  $p"
  else
    git -C "$p" pull --ff-only --quiet
    echo "pulled    $p"
  fi
done

sources=("$core" ${packs[@]+"${packs[@]}"})
for dir in skills agents hooks; do
  [ -d "$home/$dir" ] || continue
  while IFS= read -r l; do
    [ -e "$l" ] && continue
    target="$(readlink "$l")"
    for s in "${sources[@]}"; do
      case "$target" in "$s"/*)
        if [ "$dry" = 1 ]; then echo "would remove $l (target gone)"; else rm "$l"; echo "removed   $l (target gone)"; fi
        break ;;
      esac
    done
  done < <(find "$home/$dir" -maxdepth 1 -type l)
done

install_args=(${pack_args[@]+"${pack_args[@]}"})
[ "$dry" = 1 ] && install_args+=(--dry-run)
"$core/install.sh" ${install_args[@]+"${install_args[@]}"}

[ "$dry" = 1 ] || rm -f "$home/workflow-update-check.json"
echo "Start a new Claude Code session to pick up the changes."
exit 0
}
