# Teaching Jig

Jig is the workflow core these skills belong to. Its topic workspace is `~/.claude/teach/jig/`. The skill folder is usually a symlink, so find Jig's own folder with `cd -P <this skill's folder>/../.. && pwd`, called `<jig>` below.

## Sources

Jig's own docs are the sources, and the only ones. Seed `RESOURCES.md` with them in the first session:

| File | Reach for it for |
|---|---|
| `<jig>/README.md` | What Jig is, its principles, installing, its scripts and tests |
| `<jig>/docs/guide.md` | The aims, the loop, the skill table, project settings, grading and autonomy, packs |
| `<jig>/docs/decisions.md` | Why each choice was made |
| `<jig>/GLOSSARY.md` | Jig's terms |
| `<jig>/skills/<skill>/SKILL.md` | How one skill works, step by step |

**Point, never copy.** A lesson links to the file and names the heading, and quotes at most one line. A reference document is a map of where each answer lives, not a summary of it. The workspace `GLOSSARY.md` uses Jig's terms as `<jig>/GLOSSARY.md` defines them and links to that file rather than defining them again; it adds only words the user needed that Jig's glossary lacks.

**The docs win.** Jig changes. Record Jig's commit (`git -C <jig> rev-parse --short HEAD`) in each lesson. At the start of each session, `git -C <jig> log --oneline <last lesson's commit>..HEAD -- README.md docs GLOSSARY.md skills` lists what changed since; re-read those parts before teaching them, and supersede any learning record they make wrong.

## What to teach

The usual mission is to get real work done with Jig in the user's own repositories. Ask anyway; it decides the order. Without a better signal from the learning records, a sensible order is:

1. The aims and the loop, from the guide.
2. Setting up a repository: `setup-workflow` and the project settings.
3. The main flow, one step per lesson: `grill-with-docs` → `to-spec` → `to-tickets` → `implement-spec` or `implement` → `review-change` → `retro` and `grade-run`.
4. Grading and the autonomy ladder.
5. Step additions and packs.
6. The other skill groups in the guide's skill table, as the mission needs them.

## Practice

The tight feedback loop is Jig's own scripts, run on one of the user's repositories or a throwaway one: `settings.py check`, `settings.py steps <step>`, `ledger.py level` and the rest the guide names. Ask the user to predict the output, then run it.

Scenario quizzes work well for the flow: describe a situation (an idea with open questions, a settled spec, a merged change) and ask which skill comes next, which step addition loads, or which checkpoint waits at a given autonomy level. Check each answer against the doc and give the file and heading.
