#!/usr/bin/env bash
# Cut the next Jig release from main: work out the version and notes, confirm, then tag and publish.
#
# Usage: ./release.sh [--major] [--dry-run] [--yes]
#
# The version comes from the commit titles since the last vX.Y.Z tag (merges ignored):
#   every title starts with "Fix" -> patch (1.0.0 -> 1.0.1)
#   anything else                 -> minor (1.0.0 -> 1.1.0)
#   --major                       -> major (1.4.2 -> 2.0.0), only ever by hand
# The notes are those titles, oldest first. It shows both and asks before changing anything;
# --yes skips the question (needed without a terminal), --dry-run stops after showing them.
# Main must not be behind origin/main. Local commits not yet pushed are pushed with the tag.
# Then it pushes an annotated tag and the release branch at it in one atomic push, and runs gh release create.
# JIG_GH overrides the gh command (used by the tests).
set -euo pipefail

core="$(cd "$(dirname "$0")" && pwd)"
gh="${JIG_GH:-gh}"
major=0
dry=0
yes=0
while [ $# -gt 0 ]; do
  case "$1" in
    --major) major=1; shift ;;
    --dry-run) dry=1; shift ;;
    --yes) yes=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

g() { git -C "$core" "$@"; }

branch="$(g rev-parse --abbrev-ref HEAD)"
[ "$branch" = main ] || { echo "releases are cut from main; you are on $branch" >&2; exit 1; }
g fetch --quiet --tags origin main
behind="$(g rev-list --count HEAD..origin/main)"
[ "$behind" = 0 ] || { echo "main is $behind commit(s) behind origin/main; pull first" >&2; exit 1; }
ahead="$(g rev-list --count origin/main..HEAD)"

last="$(g tag -l 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -n 1 || true)"
if [ -n "$last" ]; then
  titles="$(g log --no-merges --reverse --format=%s "$last..HEAD")"
else
  titles="$(g log --no-merges --reverse --format=%s HEAD)"
fi
[ -n "$titles" ] || { echo "nothing to release: no commits since $last"; exit 0; }

IFS=. read -r x y z <<< "${last#v}"
x="${x:-0}"; y="${y:-0}"; z="${z:-0}"
if [ "$major" = 1 ]; then
  next="v$((x + 1)).0.0"
elif ! printf '%s\n' "$titles" | grep -qvE '^Fix(es|ed)?( |$)'; then
  next="v$x.$y.$((z + 1))"
else
  next="v$x.$((y + 1)).0"
fi
notes="$(printf '%s\n' "$titles" | sed 's/^/- /')"

echo "Release $next (last: ${last:-none})"
[ "$ahead" = 0 ] || echo "Also pushes $ahead unpushed commit(s) on main."
echo
echo "$notes"
echo
[ "$dry" = 1 ] && exit 0

if [ "$yes" = 0 ]; then
  [ -t 0 ] || { echo "no terminal to confirm on; rerun with --yes" >&2; exit 1; }
  read -r -p "Tag, push and publish $next? [y/N] " answer
  case "$answer" in [yY]*) ;; *) echo "stopped; nothing changed"; exit 1 ;; esac
fi

[ "$ahead" = 0 ] || g push --quiet origin main
g tag -a "$next" -m "$next"
g push --quiet --atomic origin "$next" "$next^{commit}:refs/heads/release" || {
  g tag -d "$next" >/dev/null
  echo "push rejected; nothing reached origin and the local tag $next is removed" >&2
  exit 1
}
(cd "$core" && "$gh" release create "$next" --title "$next" --notes "$notes")
echo "released  $next"
