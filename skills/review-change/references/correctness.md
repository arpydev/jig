# Correctness checklist

For the Correctness reviewer. These are runtime edge cases that type checks and unit tests miss, collected from past reviews.

## Weakened safeguards

Read the diff's deletions and edits, not just its additions, for checks that got looser: validation (minimum and maximum lengths, required fields), `if`/`throw` guards, conditional writes, authorisation checks, permissions and grants, flag checks, and tests that were deleted or had their expectations changed. List each with its reason, or say it should be put back. If the spec or plan has a "must not change" list, check each item is proven.

## Edge cases

For each changed file, ask:

- What can each external value really be (empty string, null, missing, extra field)? Does every schema accept it? A frontend schema stricter than what the backend can send makes a whole list fail to parse.
- On every async path: what happens on error, cancel, timeout and early return? Is any state left set, such as a loading flag left on when the input changes mid-request? Does a read made straight after a write (a reload, a re-fetch, a status check) use a consistent read, or can it show the state from before the write?
- Is any error caught and turned into a normal-looking result, such as an infrastructure failure reported as "not found"? Is that deliberate and logged?
- Does it assume a row, setting or env var exists for every tenant and environment?
- What happens under throttling or partial responses (unprocessed items in a batch, retries without backoff, unbounded loops)? When mapping a provider error to a status, list every code it can carry and decide each one.
- Can the write run twice? What happens the second time?
- Does the request write to more than one place? List every way each write can fail, including lookups inside services it calls. Order the writes so any failure leaves a state the user can retry, and log whatever a failure leaves behind. Don't accept "rare" without tracing it.
- Is every free-text input capped well below the store's limits?
- Does a fix depend on how the user arrived (history, the previous page, a click handler)? Check every way of arriving (new tab, bookmark, sign-in redirect, modifier-click) and every role on each.
- Input-device and rate edge cases: does a fixed step or a handler run away on a fast or high-resolution input, such as a trackpad?

## Tests

- A behaviour the change adds or relies on that no test would catch if it broke.
- A tautological test: an assertion that recomputes the expected value the way the code does, or a test that would still pass if the behaviour it names were broken. Break the behaviour in your head and check the test would go red.
- A test, file or code path the change adds that nothing in the spec or ticket needs.
