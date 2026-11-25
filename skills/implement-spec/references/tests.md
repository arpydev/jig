# Every new test must catch something real

A test only ever seen passing may just describe the code rather than guard it.

**Pick inputs that isolate the case.** Vary only what the guard depends on and keep everything else equal, so the test can't pass for another reason. Inputs copied from real data often share a prefix, suffix or whole-number part and skip the hard case. A test meant to fail for one guard shouldn't also trip another.

**Break the code and watch tests go red.** Either write the test before the code, or break the behaviour it protects (remove a check, swap an order, change a value), run the tests, then restore the file and show it's identical to a backup. Aim:

- at least one break at each new test, not just at each behaviour, or narrow tests slip through;
- at what the change relies on but didn't write (effects, memo dependencies, reset paths);
- at the user sequences around it: arrive one way and leave another, change an input twice, type then switch. Breaking only the added lines misses state carried between steps.

**Report a break table**, one row per break with the tests that went red. Then act on two things:

- a test that never fails under any break: delete it or make it assert something;
- a behaviour no break catches: add a test.

A test that passes only because an older check already holds is a "must not change" test; prove it by breaking that older check.

**Scripting the breaks:** capture stdout and stderr (some test runners report failures on stderr), anchor each break on text that appears once in the file, and run the formatter before the harness. Restore from the backup copy only, never with `git checkout` or `git restore`: the file also holds your uncommitted change. A table with no red at all means the harness is broken until one break has been shown red by hand.

**Keep output short.** Every line of output is re-sent on each later turn. Run tests with a terse reporter and keep the tail (`set -o pipefail; <test command> 2>&1 | tail -40`). When something fails, re-run just that file for its full output. Keep `pipefail`, or a failing run reads as a pass.
