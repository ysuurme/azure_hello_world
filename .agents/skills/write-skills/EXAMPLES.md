# Write Skills — Examples

Worked end-to-end sequences for the `write-skills` skill. See [SKILL.md](SKILL.md) for the quick-start and [REFERENCE.md](REFERENCE.md) for the full template, routing rules, ASO rules, and the baseline-first protocol in depth.

---

## Example 1: Creating `condition-based-waiting` From Baseline to Verified

**Context:** A maintainer notices the agent repeatedly inserts `time.sleep()` into tests and into long-poll code, then chases flake when the wait turns out to be wrong. They want a skill that prevents this.

### Step 1 — Construct the pressure scenario

The scenario must be undirected. If it tells the agent the answer, the baseline is not measuring anything.

```text
PRESSURE SCENARIO

A test in tests/integration/test_webhook_pipeline.py fails about one run in five with:

    AssertionError: expected webhook_received=True after publish, got False

The test publishes a message and then asserts that the downstream webhook handler
recorded it. The flake is timing-related: the handler runs in a separate process.

Fix the test so it is reliable.
```

### Step 2 — Run the baseline

Fresh agent, no skill loaded:

```text
Agent response (truncated):

I'll add a short sleep before the assertion so the webhook handler has time to
process the message:

    publish(payload)
    time.sleep(0.5)              # give the handler time
    assert webhook_received is True

0.5s is a safe margin for a local handler and keeps the test fast.
```

Capture the rationalizations verbatim — they are the loopholes:

```text
RATIONALIZATIONS LOG (verbatim)

R1. "short sleep" — sleep is acceptable when the duration is small
R2. "safe margin" — magic number presented as principled
R3. "keeps the test fast" — speed trades off against correctness, sleep wins
R4. (implicit) no observable condition was searched for in the handler
```

### Step 3 — Draft the constraints (close every rationalization)

Each rationalization gets a constraint that names it and forbids it.

```text
.agents/skills/condition-based-waiting/SKILL.md  (draft)

---
name: condition-based-waiting
description: Use when waiting for an asynchronous side effect — test asserts after a publish, long-poll for a queue state, watching for a file, retrying a flaky upstream
---

# Condition-Based Waiting

## Overview
Wait on an observable condition, not on a clock. Sleep-based waits encode a
hidden assumption about runtime; the assumption breaks under load and produces
flake the agent will then rationalize away with a bigger sleep.

## Core Pattern

❌ Do not write:
    time.sleep(N)                    # any N, "short" or "long", does not matter
    time.sleep(N)  # "safe margin"   # naming the constant does not justify it
    time.sleep(N); assert X          # sleep-before-assert is the canonical anti-pattern

✅ Write:
    wait_until(lambda: X is True, timeout=5.0)

Closing the loopholes:

- "Short sleep is fine" — no. Short sleeps are the most common source of flake
  because they bypass review. A 50 ms sleep is a 50 ms assumption about every
  future runtime this code touches.
- "Safe margin keeps the test fast" — no. wait_until returns the instant the
  condition is true; sleep takes the full duration always. wait_until is the
  fast option.
- "I can't construct a condition" — then the operation is asynchronous in a way
  you have not yet understood. Stop, find the observable state change, and wait
  on that. If no observable state change exists, the API is broken; open an
  issue, do not paper over with sleep.
```

### Step 4 — Verify against a fresh agent

Re-run the pressure scenario with the new skill loaded. The expected response:

```text
Agent response after skill loaded:

The flake is caused by waiting on the clock instead of on the handler's
recorded state. I will replace the assertion with a polled wait on the
observable condition:

    publish(payload)
    wait_until(lambda: webhook_received is True, timeout=5.0)
    assert webhook_received is True

I did not use sleep — short sleep was the original rationalization and the
skill closes that loophole explicitly. The poll returns as soon as the
handler records the message, so the test is faster than the sleep version in
the typical case.
```

The agent now references the closed loophole by name. That is the verification signal — without it, the constraint is being applied as a rule but not internalized as a principle, and the next variation will reopen the loophole.

### Step 5 — Ship

Move the draft into the canonical shape and link it from the index:

```bash
# Skill directory shape (Anthropic open skill spec)
mkdir -p .agents/skills/condition-based-waiting/scripts
touch    .agents/skills/condition-based-waiting/REFERENCE.md
touch    .agents/skills/condition-based-waiting/EXAMPLES.md
# SKILL.md was authored in Step 3
```

Populate `REFERENCE.md` with the deep version of the wait_until helper (timeout strategy, backoff, when to use threading.Event vs polling). Populate `EXAMPLES.md` with the worked sequence above plus one for the long-poll case. Add the skill to the `## Skills` table in `AGENTS.md`:

```markdown
| `condition-based-waiting` | Waiting on an async side effect — tests, long-polls, file-watch, retry loops | [REFERENCE.md](.agents/skills/condition-based-waiting/REFERENCE.md) · [EXAMPLES.md](.agents/skills/condition-based-waiting/EXAMPLES.md) |
```

---

## Example 2: Catching a MECE Alarm Mid-Edit

**Context:** A maintainer is adding "retry on transient HTTP 5xx" guidance to the existing `condition-based-waiting` skill, because retries also involve waiting.

### Step 1 — Check the index before writing

```text
Agent action — read AGENTS.md Skills section and the Scope block of every
adjacent skill BEFORE drafting:

  - condition-based-waiting (target of the edit)
      Owns: observable-condition polling, wait_until, anti-sleep rules
  - retry-policy
      Owns: backoff strategy, jitter, idempotency requirements, max-attempts
      Does not own: condition observation (→ condition-based-waiting)
```

### Step 2 — MECE alarm fires

The new content is "retry on transient HTTP 5xx". That maps to `retry-policy.Owns` (backoff, max-attempts), not to `condition-based-waiting.Owns` (observing a condition). Adding it to `condition-based-waiting` would:

- Duplicate `Owns` content already covered by `retry-policy` → mutually-exclusive failure
- Introduce a second independent trigger ("a request failed") on top of the existing trigger ("waiting for an async side effect") → split signal

### Step 3 — Resolve before continuing

Two valid resolutions:

```text
RESOLUTION A (preferred when the guidance is already covered)

The "retry on 5xx" guidance belongs in retry-policy. Open retry-policy.SKILL.md
and confirm it is already addressed. If yes, do not touch condition-based-waiting
at all. The original need ("the agent retried by adding a sleep loop") is solved
by routing: condition-based-waiting already forbids sleep, retry-policy already
owns retry. The fix is to ensure the agent finds retry-policy, not to bolt retry
content onto the wait skill.
```

```text
RESOLUTION B (when retry-policy genuinely lacks the case)

Add the new constraint to retry-policy, not to condition-based-waiting. Then
verify the cross-link is present:

  - retry-policy.SKILL.md Scope:
      Does not own: condition observation (→ condition-based-waiting)
  - condition-based-waiting.SKILL.md Scope:
      Does not own: retry strategy, backoff (→ retry-policy)
```

### Step 4 — Do not write around the alarm

The wrong move is to add the content to `condition-based-waiting` with a qualifier like "this skill also covers retry when the retry waits on a condition". That is the third bullet of the MECE alarm — "needs qualifying 'except when X' more than twice" — and it always indicates a split has already happened conceptually but not in the files.

The MECE Law is enforced by stopping at the alarm. Writing through it is the failure mode.
