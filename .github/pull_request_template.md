## What changed

<!-- One short paragraph. What a reader of the diff needs to know. -->

## Why

<!-- In terms of the end user, or the rule being protected. -->

## How it was verified

<!-- Commands run, tests added, numbers checked by hand. -->

Closes #

---

## Review checklist

**The five rules**

- [ ] No buy, sell, hold, target or top pick language anywhere, including
      comments and test names
- [ ] No estimated, approximated or proxy number. Anything not computable to its
      real definition is switched off with a stored reason
- [ ] No upstream provider name in code, comments, documentation, schema,
      fixtures, logs or interface copy
- [ ] No metric computed in the browser
- [ ] Filter and rank remain separate

**Data honesty**

- [ ] New fact columns carry `source` and `as_of`
- [ ] A missing value cannot pass a filter, and is counted separately from a
      failure
- [ ] New reference data is downloaded or derived, never typed

**Engineering**

- [ ] Fetching and computing are not mixed in one module
- [ ] Errors are raised, nothing returns an empty result on failure
- [ ] Ingest stays checkpointed and idempotent
- [ ] New checks can fail the run, not only print
- [ ] Pure logic is testable without a network
- [ ] Module docstrings state what the module refuses to do

**Hygiene**

- [ ] `pytest -q` passes
- [ ] No secret, token, data file or log in the diff
- [ ] `STATUS.md` or `mvp/tasks.json` updated if a decision changed
