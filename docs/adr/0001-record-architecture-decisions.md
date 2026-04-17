# 1. Record architecture decisions

Date: 2026-04-17

## Status

Accepted

## Context

Wir starten ein mehrstufiges Refactoring (siehe [`ROADMAP.md`](../../ROADMAP.md))
mit dem Ziel, daikin_onecta auf das Engineering-Niveau von
[`aiohomematic`](https://github.com/SukramJ/aiohomematic) zu heben. Die
geplanten Schritte umfassen Tooling, Test-Ausbau, Domain-Model-Extraktion und
Robustheits-Patterns. Solche Entscheidungen müssen nachvollziehbar bleiben,
damit künftige Beitragende — auch Monate später — verstehen, warum eine
bestimmte Struktur gewählt wurde.

## Decision

Wir führen Architecture Decision Records (ADRs) im Format von Michael Nygard
unter `docs/adr/` ein. Jede ADR ist eine eigene Markdown-Datei mit dem Schema
`NNNN-titel-mit-bindestrichen.md` und enthält die Sektionen **Status**,
**Context**, **Decision** und **Consequences**.

Erfasst werden nur Entscheidungen, die strukturelle Auswirkungen haben:
neue Pakete, Schichtgrenzen, Wahl von Bibliotheken/Mustern, Breaking Changes
am internen API.

## Consequences

- Jede strukturelle Änderung muss von einer neuen ADR begleitet werden.
- Status alter ADRs wird auf `Superseded by ADR NNNN` aktualisiert, statt sie
  zu löschen.
- ADRs sind Teil der Code-Review: ohne ADR keine strukturelle Änderung.
- Die ROADMAP-Phasen 5, 6, 7 und 10 produzieren ADRs (Exception-Hierarchie,
  Retry/Circuit-Breaker-Strategie, Domain-Model, Doku-Format).
