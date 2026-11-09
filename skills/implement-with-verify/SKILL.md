---
name: implement-with-verify
description: Implement work from a spec or tickets, verify it by exercising the running change, then review it.
disable-model-invocation: true
---

# Implement with verify

Implement the work described by the user in the spec or tickets.

If the user passes a ticket reference, fetch it from the issue tracker and state its title before starting. If the reference is ambiguous, ask.

Call the Skill tool with "tdd" where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once green, call the Skill tool with "verify-implementation", passing the spec and the change set. When the work spans several independent tickets, verify each ticket as it lands rather than once at the end. Implementation is done when every scenario in the verification matrix is pass, fixed, or escalated and answered by the user.

Once verified, call the Skill tool with "code-review" to review the work.
