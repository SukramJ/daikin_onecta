# 1. Record architecture decisions

Date: 2026-04-17

## Status

Accepted

## Context

We are starting a multi-phase refactor (see [`ROADMAP.md`](../../ROADMAP.md))
with the goal of bringing daikin_onecta up to the engineering level of
[`aiohomematic`](https://github.com/SukramJ/aiohomematic). The planned steps
cover tooling, test expansion, domain-model extraction, and resilience
patterns. Such decisions must remain traceable so that future contributors —
even months later — understand why a particular structure was chosen.

## Decision

We adopt Architecture Decision Records (ADRs) in the format proposed by
Michael Nygard under `docs/adr/`. Each ADR is its own Markdown file using the
naming scheme `NNNN-title-with-hyphens.md` and contains the sections
**Status**, **Context**, **Decision**, and **Consequences**.

We only record decisions with structural impact: new packages, layer
boundaries, choice of libraries/patterns, breaking changes to the internal
API.

## Consequences

- Every structural change must be accompanied by a new ADR.
- The status of older ADRs is updated to `Superseded by ADR NNNN` rather than
  being deleted.
- ADRs are part of code review: no structural change without an ADR.
- ROADMAP phases 5, 6, 7, and 10 will produce ADRs (exception hierarchy,
  retry/circuit-breaker strategy, domain model, documentation format).
