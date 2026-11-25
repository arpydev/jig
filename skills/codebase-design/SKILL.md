---
name: codebase-design
description: Shared vocabulary for designing deep modules (module, interface, depth, seam, adapter, leverage, locality), the deletion test, and the rules for keeping code and infrastructure simple and easy to change. Use when planning data, statuses or infrastructure, finding deepening opportunities in the area a ticket touched, deciding where a seam goes, making code easier to test, or when another skill (the retro's architecture check) needs the deep-module vocabulary.
---

<!-- Local fork of mattpocock/skills codebase-design (MIT, see ../../LICENSE-mattpocock-skills). The upstream/ folder holds the version this fork was taken from. Every local change is listed under "Local changes" at the end. -->


# Codebase Design

Design **deep modules**: a lot of behaviour behind a small interface, placed at a clean seam, testable through that interface. Use this language and these principles wherever code is being designed or restructured. The aim is leverage for callers, locality for maintainers, and testability for everyone.

## Glossary

Use these terms exactly: don't substitute "component," "service," "API," or "boundary." Consistent language is the whole point.

**Module**: anything with an interface and an implementation. Deliberately scale-agnostic: a function, class, package, or tier-spanning slice. _Avoid_: unit, component, service.

**Interface**: everything a caller must know to use the module correctly: the type signature, but also invariants, ordering constraints, error modes, required configuration, and performance characteristics. _Avoid_: API, signature (too narrow, they refer only to the type-level surface).

**Implementation**: what's inside a module, its body of code. Distinct from **Adapter**: a thing can be a small adapter with a large implementation (a Postgres repo) or a large adapter with a small implementation (an in-memory fake). Reach for "adapter" when the seam is the topic; "implementation" otherwise.

**Depth**: leverage at the interface. The amount of behaviour a caller (or test) can exercise per unit of interface they have to learn. A module is **deep** when a large amount of behaviour sits behind a small interface, **shallow** when the interface is nearly as complex as the implementation.

**Seam** _(Michael Feathers)_: a place where you can alter behaviour without editing in that place; the *location* at which a module's interface lives. Where to put the seam is its own design decision, distinct from what goes behind it. _Avoid_: boundary (overloaded with DDD's bounded context).

**Adapter**: a concrete thing that satisfies an interface at a seam. Describes *role* (what slot it fills), not substance (what's inside).

**Leverage**: what callers get from depth. More capability per unit of interface they learn. One implementation pays back across N call sites and M tests.

**Locality**: what maintainers get from depth. Change, bugs, knowledge, and verification concentrate in one place rather than spreading across callers. Fix once, fixed everywhere.

## Deep vs shallow

**Deep module** = small interface + lots of implementation:

```
┌─────────────────────┐
│   Small Interface   │  ← Few methods, simple params
├─────────────────────┤
│                     │
│  Deep Implementation│  ← Complex logic hidden
│                     │
└─────────────────────┘
```

**Shallow module** = large interface + little implementation (avoid):

```
┌─────────────────────────────────┐
│       Large Interface           │  ← Many methods, complex params
├─────────────────────────────────┤
│  Thin Implementation            │  ← Just passes through
└─────────────────────────────────┘
```

When designing an interface, ask:

- Can I reduce the number of methods?
- Can I simplify the parameters?
- Can I hide more complexity inside?

## Principles

- **Depth is a property of the interface, not the implementation.** A deep module can be internally composed of small, mockable, swappable parts; they just aren't part of the interface. A module can have **internal seams** (private to its implementation, used by its own tests) as well as the **external seam** at its interface.
- **The deletion test.** Imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.
- **The interface is the test surface.** Callers and tests cross the same seam. If you want to test *past* the interface, the module is probably the wrong shape.
- **One adapter means a hypothetical seam. Two adapters means a real one.** Don't introduce a seam unless something actually varies across it.

## Designing for testability

Good interfaces make testing natural:

1. **Accept dependencies, don't create them.**

   ```typescript
   // Testable
   function processOrder(order, paymentGateway) {}

   // Hard to test
   function processOrder(order) {
     const gateway = new StripeGateway();
   }
   ```

2. **Return results, don't produce side effects.**

   ```typescript
   // Testable
   function calculateDiscount(cart): Discount {}

   // Hard to test
   function applyDiscount(cart): void {
     cart.total -= discount;
   }
   ```

3. **Small surface area.** Fewer methods = fewer tests needed. Fewer params = simpler test setup.

## Relationships

- A **Module** has exactly one **Interface** (the surface it presents to callers and tests).
- **Depth** is a property of a **Module**, measured against its **Interface**.
- A **Seam** is where a **Module**'s **Interface** lives.
- An **Adapter** sits at a **Seam** and satisfies the **Interface**.
- **Depth** produces **Leverage** for callers and **Locality** for maintainers.

## Rejected framings

- **Depth as ratio of implementation-lines to interface-lines** (Ousterhout): rewards padding the implementation. We use depth-as-leverage instead.
- **"Interface" as the TypeScript `interface` keyword or a class's public methods**: too narrow: interface here includes every fact a caller must know.
- **"Boundary"**: overloaded with DDD's bounded context. Say **seam** or **interface**.


## The repo's own patterns win

A repo's documented patterns override this skill. Run `python3 ~/.claude/skills/setup-workflow/scripts/settings.py steps design`, read each file it prints and load each `skill:<name>`: they name the repo's patterns and where they are written down. Don't propose removing anything the pattern docs require, such as an agreed port, or anything else the pattern docs rule out. Look for depth inside that layout: services whose interface is nearly as big as their body, logic spread across several services or handlers that belongs in one, and the same rule written in more than one place.

## Simple and easy to change

This applies to code and to infrastructure: tables, indexes, queues, Lambdas, stacks and IAM. The aim is the smallest change that works today, with a clear way to grow if the need comes.

- **One place for each fact.** Before adding a field, status, flag, table or index, look for one that already holds that fact, and extend it (a new value on the existing `status`) rather than adding a parallel one (an `escalationStatus` next to `status`). Two fields for one fact drift apart, and every reader has to know which one to trust.
- **Build for the access patterns the ACs need now.** List each read and write, then map each one to an existing key or index. Add a table, index, queue, Lambda, construct or stack only for a pattern nothing existing can serve.
- **Think hardest where change is expensive.** A DynamoDB table's partition and sort keys, and any name another system reads (events, API fields, statuses), are hard to change later. Attributes, GSIs, Lambdas, queues and alarms are cheap to add later (DynamoDB backfills a new GSI on a live table), so don't add them in advance.
- **Write down how it would grow; don't build it.** One line is enough, for example "if support staff need to filter by region, add a GSI on regionCode". That line is how the design handles growth.
- **Reuse before adding.** Use the existing construct, stack and patterns first. Grant IAM actions only for the calls the code makes.
- **Remove what nothing reads.** An index, field, env var or grant with no reader still costs something and suggests a need that doesn't exist. Remove it in the same change, or raise a tech-debt ticket.
- **Fewer moving parts.** Prefer one Lambda or one step over a chain, unless retries, scaling or ownership need them apart.

## Code that explains itself

Every doc and comment has to be loaded into context and can drift out of date. Names, types and tests can't drift without the build or tests noticing.

- **Readers should get their answers from the code.** Names, types and tests carry the meaning. Before writing a comment or a doc, try these first: rename, extract a named function or constant, narrow a type (a union of statuses rather than a string), or write a test whose name states the rule.
- **A comment that explains which of two behaviours applies usually means the decision hasn't been made.** Make the decision and put it in the code.
- **A comment is fine only for a reason the code can't show.** Examples are a quirk of an external system, a regulatory rule, or a deliberate choice that looks wrong. Keep it to one line saying why, not what. If a test can prove that reason, use the test instead.
- **Don't write docs that repeat the code.** If the code can prove what a doc says, generate the doc with a script or replace it with a check.
- **Remove stale or redundant comments in the code you touch, in the same change.**

## Going deeper

- **Deepening a cluster given its dependencies**, see [DEEPENING.md](DEEPENING.md): dependency categories, seam discipline, and replace-don't-layer testing.
- **Exploring alternative interfaces**, see [DESIGN-IT-TWICE.md](DESIGN-IT-TWICE.md): spin up parallel sub-agents to design the interface several radically different ways, then compare on depth, locality, and seam placement.

## Local changes

Taken 2026-11-23 from github.com/mattpocock/skills at commit abeeaf9 (`skills/engineering/codebase-design/`, MIT licence). `upstream/improve-codebase-architecture.md` is the command this fork's retro check is based on. When upstream changes, diff it against `upstream/`, carry the changes in, keep the changes below, then replace `upstream/`.

| Date | Change | Why | Upstream? |
|---|---|---|---|
| 2026-11-23 | "The repo's own patterns win" section; the repo's agreed ports are exempt from the one-adapter rule (named in the `design` step addition) | A repo's agreed patterns would otherwise be flagged everywhere | Local only |
| 2026-11-23 | "Simple and easy to change" section, covering infrastructure as well as code | The developer wants tight infra and code that works with the smallest change and can still grow; unneeded fields and indexes had crept into planned work | Propose upstream |
| 2026-11-24 | "Code that explains itself" section | The developer wants answers readable from the code, not from docs or comments, so less is loaded into context and nothing drifts; a comment often means a decision wasn't made | Propose upstream |
| 2026-11-23 | Description names the retro architecture check | So the skill loads from the retro | Local only |
| 2026-11-24 | A project's ports detail and examples moved to a pack's `design` step addition | The core holds no company facts | Local only |
