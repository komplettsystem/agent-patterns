# Agent Guidelines: Code

Additions to [AGENT-BASE.md](AGENT-BASE.md) for projects with code. The base rules still
apply; these make them concrete.

## Tests come first

Rule 3 for code: write a test that fails for the right reason, then make it pass.

- A bug fix starts with a test that reproduces the bug.
- Test behaviour a user or caller would notice, not internal details.
- Skipping tests is allowed for throwaway spikes. Say so explicitly and note that tests are owed.

## Look up interfaces, don't guess them

Rule 2 for code: read the actual function signatures, data shapes and module boundaries
before calling or changing them. If the source isn't available, say what you assumed.

## Let errors surface

Rule 5 for code: no `try`/`except` or `catch` blocks that swallow errors, and no fallback
values nobody asked for. If a fallback would help, propose it and let the owner decide.

## Clean up only what you caused

Rule 6 for code: remove imports, variables and functions that *your* change left unused.
Leave pre-existing dead code alone and mention it.

## Keep the diff reviewable

A reviewer should be able to tell from the diff alone what changed and why. Separate
refactoring from behaviour changes, and don't mix formatting into either.
