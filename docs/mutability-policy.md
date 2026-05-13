# Mutability Policy

This repo enforces Vyper mutability labels with `tools/mutability_scanner.py`.

## Rules

- `@view` and `@pure` functions must not contain `assert`, `raise`, or `raw_revert`.
- Any `@external` or `@internal` function that compiles as `@view` must be labeled `@view`.
- Any existing `@view` function that compiles as `@pure` must be labeled `@pure`.
- Local `.vy` interface declarations must match the mutability of a unique matching external implementation.

The scanner uses the pinned local Vyper compiler for promotion checks. Do not rely on static string matching for `@pure`; compiler output is the source of truth, especially when immutables are involved.

## Baseline

`tools/mutability-baseline.yml` is generated with:

```bash
python tools/mutability_scanner.py --write-baseline tools/mutability-baseline.yml
```

Normal runs must not use `--write-baseline`:

```bash
python tools/mutability_scanner.py --baseline tools/mutability-baseline.yml
```

After the initial cleanup baseline is created, remove entries as violations are fixed. Do not add new entries during cleanup. A new unbaselineed violation fails the scanner. A stale baseline entry also fails, so fixing a violation requires removing its baseline entry.

## Exemptions

Inline exemptions are only for urgent unrelated work and should not be part of the target final state:

```vyper
# mutability-exempt[view-revert]: single-line reason
@view
@external
def foo(...):
    ...
```

Allowed categories are:

- `view-revert`
- `can-be-view`
- `view-could-be-pure`

The reason must be non-empty and single-line. The exemption must be the immediate line above the topmost decorator, with no unrelated comments between the exemption and the decorator.

## Refactor Pattern

When a view helper currently reverts, prefer returning a sentinel from the helper and asserting in the non-view caller.

- Address result: return `empty(address)` on failure.
- Boolean/data result: return `(False, data)` or `(False, default_data)`.
- Numeric tuple: return zeros only if the caller checks and zero is unambiguous.
- Multi-error helpers should return a local status code and preserve existing `dev:` strings with branched caller asserts.

Do not introduce shared status-code modules only for mutability cleanup.
