# Cleanup-tests reference

Read this during classification. This is the canonical, standalone cleanup
rubric and test-quality reference for this workflow.

## Local test-quality principles

- Read repository `CONTEXT.md` when present and relevant ADRs before naming
  contracts or seams. Use the repository's domain vocabulary.
- A valuable test verifies observable behavior through a public interface or
  seam, reads like a specification, and survives internal refactors.
- A seam is the public boundary where behavior is observed. Use documented or
  user-confirmed seams; do not write or rewrite tests at an unconfirmed seam.
- Implementation coupling includes private methods, internal collaborators or
  mocks, call count/order, and verification through side channels. Boundary
  mocks are allowed only for external APIs, time/randomness, filesystem, and
  sometimes databases; prefer a test database when practical. Do not mock
  owned or internal modules.
- Tautological expectations require an independent source of truth from the
  evidence ladder below.
- Preserve one logical behavior/assertion per test. Parameterized rows may share
  a shape, but each row must remain independently named and diagnosable.
- Cleanup edits are review/refactoring of existing tests, not a red-green
  production implementation loop. Preserve observable behavior and never add
  speculative coverage or features.

## Independent evidence ladder

Use the strongest available independent source for a protected contract:

1. explicit specification or domain rule;
2. accepted example or fixture; or
3. an independently worked literal expected value.

The implementation, a private helper, a coverage report, or the current test
assertion is not independent contract evidence. If the ladder does not resolve
expected behavior, record `unclear contract` as unresolved and do not guess a
repair. A mutation probe can supplement execution-path/test-sensitivity
evidence only; it can never establish contract, provenance, expected values,
duplicate equivalence, or deletion safety.

## Canonical categories

Every finding uses one or more values from this enum, and no other category
names:

`tautological | low-value | duplicate | snapshot | flaky | slow | unreadable`

| Category | Require | Do not infer |
| --- | --- | --- |
| tautological | the expectation recomputes or restates the implementation | that a different assertion is correct without independent evidence |
| low-value | implementation-detail coupling, internal mocks, trivial language/framework checks, impossible/unreachable states, incidental call count/order, or stronger public-seam coverage makes the test non-contractual | that every cheap test is disposable; keep cheap unique contract/regression protection |
| duplicate | same observable contract, conditions, execution path, and failure signal | duplication from code similarity or shared setup |
| snapshot | output is oversized, unstable, implementation-shaped, weakly reviewable, or duplicative | that all snapshots are bad; a focused stable public output may remain |
| flaky | inconsistent controlled repetitions or a concrete nondeterministic dependency such as time, randomness, order, concurrency, network, or shared state | flakiness from one failure or intuition |
| slow | a documented budget, measured relative outlier, or concrete structural cause such as real sleep, repeated expensive setup, redundant boot, or avoidable external I/O | slowness from intuition alone |
| unreadable | protected contract, setup-action-assertion flow, important data, or failure meaning is obscured | formatter/linter cosmetics |

Keep distinct behaviors separate. A merge is valid only for same-contract,
same-shape data cases represented as parameterized or named rows. Preserve
distinct failure names, regression labels, and issue context. Preserve a cheap
test when it uniquely protects a meaningful observable contract or regression.

## Cross-cutting evidence rules

Mocks are not a category. Apply the boundary rule above: mock only external
APIs, time/randomness, filesystem, and sometimes databases; prefer a test
database when practical. Never mock owned/internal modules, including merely to
make tests faster. Internal mocks are evidence of a possible finding, not a
reason to add more mocks.

Coverage metrics are supporting evidence only. A coverage percentage, uncovered
line, or coverage increase alone never proves deletion, merging, repair, or
retention.

Fixtures and snapshots must be classified for scope separately from finding
categories. Production/runtime fixtures are never writable. A test-only
fixture/snapshot is writable only when its exact path was frozen before audit
approval.

## Classification and actions

Each test receives exactly one classification: `finding` or `keep`. `keep` is a
classification only and is never an action or approval target.

An actionable finding has independent evidence, a confirmed seam where needed,
and exactly one action from this enum:

`delete | repair | merge`

- `delete`: remove only when the meaningful contract is absent, impossible,
  duplicated by equivalent stronger coverage, or otherwise proven unnecessary.
- `repair`: replace a weak assertion or structure with an evidence-backed
  contract. Never invent expected values.
- `merge`: combine only same-contract/same-shape cases as named rows. Preserve
  distinct behaviors, failure names, regression labels, and issue context.

An unclear contract, missing provenance, unconfirmed seam, unsafe mutation,
insufficient independent evidence, or lack of a safe change is `unresolved` and
non-approvable. Do not assign it an action. Every actionable record names
verification for the affected test, relevant repetition where applicable, and
the broader command where practical.

## Audit record

Retain this internal record for every test before writing the report:

```text
test: <stable file/test identity>
contract: <observable behavior>
seam: <documented public seam | candidate | ambiguous>
coverage: <related tests and stronger seam, if any>
failure: <what failure tells a maintainer>
provenance: <spec/domain/example/fixture/regression source | missing>
classification: finding|keep
finding_ids: <stable IDs or None>
runtime: <baseline/timing/repetition evidence or blind spot>
scope: <frozen writable path | read-only path>
```

The final report may summarize this record, but it must account for every
in-scope test and disclose missing evidence.
