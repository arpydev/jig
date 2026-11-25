#!/usr/bin/env bash
# Link the core's skills, agents and hooks into ~/.claude, and optionally a pack's.
#
# Usage: ./install.sh [--pack <dir>]... [--dry-run] [--backup] [--owner yes|no]
#
# A pack is a folder with skills/, agents/ and hooks/ in the same layout as the core, and a pack.json.
# hooks/hooks.json lists the hook files to link into <claude home>/hooks/ and the entries that
# scripts/hooks.py merges into settings.json (only its own entries are ever changed or removed).
# --owner records in <claude home>/workflow-core.json whether this machine's user owns the core
# (the retro then proposes core edits rather than drafting an issue). It is asked once when the
# file is missing and a terminal is attached; otherwise owner is false.
# <claude home>/CLAUDE.md gets a line importing the core's preferences.md.
# Skills listed in pack.json "projectSkills" are not linked here: setup-workflow links them into
# the repositories that use them. Installed packs are listed in <claude home>/workflow-packs.
# Safe to rerun: a link already pointing at the right place is left alone. Anything else
# already at a target is reported as a conflict and left untouched; the script then exits 1.
# With --backup, anything already at a target is moved to <claude home>/skills-backup/ (or
# agents-backup/) and the link is made; nothing is ever deleted. A skill the core has is not
# linked from a pack: the pack's copy is reported as a duplicate until the pack drops it.
# A link whose target no longer exists (the core or a pack moved) is replaced, and so is an
# @.../preferences.md import line whose file no longer exists.
# CLAUDE_HOME overrides ~/.claude (used by the tests).
set -euo pipefail

core="$(cd "$(dirname "$0")" && pwd)"
home="${CLAUDE_HOME:-$HOME/.claude}"
dry=0
backup=0
owner=""
sources=("$core")
while [ $# -gt 0 ]; do
  case "$1" in
    --pack) [ $# -ge 2 ] || { echo "--pack takes a folder" >&2; exit 2; }; sources+=("$(cd "$2" && pwd)"); shift 2 ;;
    --dry-run) dry=1; shift ;;
    --backup) backup=1; shift ;;
    --owner) [ $# -ge 2 ] || { echo "--owner takes yes or no" >&2; exit 2; }; owner="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

conflicts=0
hook_files=()
link() {
  local src="$1" dest="$2"
  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
    echo "ok        $dest"
  elif [ -L "$dest" ] && [ ! -e "$dest" ]; then
    if [ "$dry" = 1 ]; then
      echo "would relink $dest -> $src (old target gone)"
    else
      rm "$dest"
      ln -s "$src" "$dest"
      echo "relinked  $dest -> $src (old target gone)"
    fi
  elif { [ -e "$dest" ] || [ -L "$dest" ]; } && [ "$backup" = 1 ]; then
    local keep="$(dirname "$(dirname "$dest")")/$(basename "$(dirname "$dest")")-backup/$(basename "$dest")"
    if [ -e "$keep" ] || [ -L "$keep" ]; then
      echo "CONFLICT  $dest: backup $keep already exists"
      conflicts=$((conflicts + 1))
    elif [ "$dry" = 1 ]; then
      echo "would back up $dest to $keep and link -> $src"
    else
      mkdir -p "$(dirname "$keep")"
      mv "$dest" "$keep"
      ln -s "$src" "$dest"
      echo "backed up $dest to $keep; linked -> $src"
    fi
  elif [ -e "$dest" ] || [ -L "$dest" ]; then
    echo "CONFLICT  $dest exists and is not a link to $src"
    conflicts=$((conflicts + 1))
  elif [ "$dry" = 1 ]; then
    echo "would link $dest -> $src"
  else
    mkdir -p "$(dirname "$dest")"
    ln -s "$src" "$dest"
    echo "linked    $dest -> $src"
  fi
}

project_skills() {
  [ -f "$1/pack.json" ] || return 0
  python3 -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1])).get("projectSkills", [])))' "$1/pack.json"
}

for s in "${sources[@]}"; do
  scoped="$(project_skills "$s")"
  for d in "$s"/skills/*/; do
    [ -d "$d" ] || continue
    d="${d%/}"
    if printf '%s\n' "$scoped" | grep -qxF "$(basename "$d")"; then
      echo "project   $(basename "$d") (linked per repository by setup-workflow)"
      continue
    fi
    if [ "$s" != "$core" ] && [ -d "$core/skills/$(basename "$d")" ]; then
      echo "duplicate $(basename "$d") (the core has it; the pack's copy is not linked)"
      continue
    fi
    link "$d" "$home/skills/$(basename "$d")"
  done
  for f in "$s"/agents/*.md; do
    [ -f "$f" ] || continue
    link "$f" "$home/agents/$(basename "$f")"
  done
  if [ -f "$s/hooks/hooks.json" ]; then
    hook_files+=("$s/hooks/hooks.json")
    while IFS= read -r f; do
      [ -n "$f" ] && link "$s/hooks/$f" "$home/hooks/$f"
    done < <(python3 -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1])).get("files", [])))' "$s/hooks/hooks.json")
  fi
done

if [ "${#hook_files[@]}" -gt 0 ]; then
  if [ "$dry" = 1 ]; then
    python3 "$core/scripts/hooks.py" --home "$home" --dry-run "${hook_files[@]}"
  else
    python3 "$core/scripts/hooks.py" --home "$home" "${hook_files[@]}"
  fi
fi

record="$home/workflow-core.json"
if [ -z "$owner" ] && [ ! -f "$record" ]; then
  if [ -t 0 ] && [ "$dry" = 0 ]; then
    read -r -p "Do you own the core repository (the retro edits it rather than drafting an issue)? [y/N] " answer
    case "$answer" in [yY]*) owner=yes ;; *) owner=no ;; esac
  else
    owner=no
  fi
fi
if [ -n "$owner" ]; then
  case "$owner" in yes) value=true ;; no) value=false ;; *) echo "--owner takes yes or no" >&2; exit 2 ;; esac
  if [ "$dry" = 1 ]; then
    echo "would write $record (owner: $value)"
  else
    mkdir -p "$home"
    printf '{"owner": %s}\n' "$value" > "$record"
    echo "wrote     $record (owner: $value)"
  fi
fi

import_line="@$core/preferences.md"
if [ -f "$home/CLAUDE.md" ] && ! grep -qxF "$import_line" "$home/CLAUDE.md"; then
  while IFS= read -r line; do
    [ -e "${line#@}" ] && continue
    if [ "$dry" = 1 ]; then
      echo "would replace $line with $import_line in $home/CLAUDE.md"
    else
      python3 -c 'import sys; p, old, new = sys.argv[1:]; t = open(p).read().split("\n"); open(p, "w").write("\n".join(new if l == old else l for l in t))' "$home/CLAUDE.md" "$line" "$import_line"
      echo "replaced  $line with $import_line in $home/CLAUDE.md"
    fi
    break
  done < <(grep -E '^@.*/preferences\.md$' "$home/CLAUDE.md")
fi
if [ -f "$home/CLAUDE.md" ] && grep -qxF "$import_line" "$home/CLAUDE.md"; then
  echo "ok        $home/CLAUDE.md imports preferences.md"
elif [ "$dry" = 1 ]; then
  echo "would add $import_line to $home/CLAUDE.md"
else
  mkdir -p "$home"
  if [ -s "$home/CLAUDE.md" ] && [ -n "$(tail -c 1 "$home/CLAUDE.md")" ]; then echo >> "$home/CLAUDE.md"; fi
  echo "$import_line" >> "$home/CLAUDE.md"
  echo "added     $import_line to $home/CLAUDE.md"
fi

if [ "$dry" = 0 ] && [ "${#sources[@]}" -gt 1 ]; then
  mkdir -p "$home"
  touch "$home/workflow-packs"
  for s in "${sources[@]:1}"; do
    grep -qxF "$s" "$home/workflow-packs" || echo "$s" >> "$home/workflow-packs"
  done
fi

if [ "$conflicts" -gt 0 ]; then
  echo "$conflicts conflict(s): resolve by hand, then rerun" >&2
  exit 1
fi
