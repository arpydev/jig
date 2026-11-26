"""Tests for to-tickets' publish.py."""
import os
import sys
import unittest

HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills", "to-tickets", "scripts")
sys.path.insert(0, HERE)
import publish  # noqa: E402

DRAFTS = """Intro text that isn't a ticket.

# 01: Add the lookup

## What to build

Mentions #7, which is a real issue, not a draft.

## Blocked by

- None (can start immediately).

---

# 02: Use the lookup

## What to build

Something.

## Blocked by

- #01 (the lookup)

## Likely to touch

- tests (`tests`)
"""


class PublishTest(unittest.TestCase):
    def test_parses_tickets_in_order_with_blockers(self):
        tickets = publish.parse(DRAFTS)
        self.assertEqual([(n, t, b) for n, t, _, b in tickets],
                         [(1, "Add the lookup", []), (2, "Use the lookup", [1])])
        self.assertFalse(tickets[0][2].endswith("---"))

    def test_rewrites_draft_numbers_only_in_blocked_by(self):
        body = publish.parse(DRAFTS)[1][2]
        out = publish.rewrite(body, {1: 42})
        self.assertIn("- #42 (the lookup)", out)
        first = publish.rewrite(publish.parse(DRAFTS)[0][2], {7: 99})
        self.assertIn("Mentions #7", first)

    def test_rejects_a_blocker_that_comes_later(self):
        with self.assertRaises(SystemExit):
            publish.check_order(list(reversed(publish.parse(DRAFTS))))


if __name__ == "__main__":
    unittest.main()
