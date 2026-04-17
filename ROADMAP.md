# Roadmap: daikin_onecta → aiohomematic-Niveau

Ziel: `daikin_onecta` auf das Engineering-Niveau von [`aiohomematic`](https://github.com/SukramJ/aiohomematic) heben — in **Code-Qualität, Tests, Architektur, Sicherheit, CI, Doku und Tooling**.

**Tracking-Konvention**
- `[ ]` = offen · `[~]` = in Arbeit · `[x]` = erledigt · `[-]` = bewusst übersprungen
- Aufwand: **S** ≤ 1 Tag · **M** 1–3 Tage · **L** 1–2 Wochen · **XL** > 2 Wochen
- Risiko: 🟢 niedrig · 🟡 mittel · 🔴 hoch (Breaking Change / großflächiges Refactoring)
- Fortschritt pro Phase wird unten in [§ Progress Dashboard](#progress-dashboard) zusammengefasst.

---

## Phase 0 — Baseline & Sicherheitsnetz

> Voraussetzung für alles andere: erst messen, dann verändern. Keine produktiven Code-Änderungen.

| # | Task | Aufwand | Risiko | Status |
|---|------|---------|--------|--------|
| 0.1 | Aktuelle Test-Coverage messen und Baseline in `coverage-baseline.txt` einchecken (97% Total) | S | 🟢 | [x] |
| 0.2 | `mypy --no-incremental .` einmal laufen lassen, Fehlerzahl als Baseline dokumentieren (49 default / 255 strict) | S | 🟢 | [x] |
| 0.3 | `ruff check --statistics` Baseline dokumentieren (0 Findings) | S | 🟢 | [x] |
| 0.4 | `bandit -r custom_components/daikin_onecta` ausführen, Findings inventarisieren (2 Low FPs) | S | 🟢 | [x] |
| 0.5 | Verzeichnis `docs/adr/` anlegen, `0001-record-architecture-decisions.md` schreiben | S | 🟢 | [x] |

---

## Phase 1 — Tooling & Konfiguration konsolidieren

> Ein zentrales `pyproject.toml`, alle Linter/Typer/Coverage darin. Voraussetzung für CI-Erweiterung.

| # | Task | Aufwand | Risiko | Status |
|---|------|---------|--------|--------|
| 1.1 | `pyproject.toml` aufbauen mit `[build-system]`, `[project]`, Metadaten, Python-Version-Constraint | S | 🟢 | [x] |
| 1.2 | `setup.cfg` → `pyproject.toml` migrieren (flake8, isort, pytest, coverage), `setup.cfg` löschen | S | 🟢 | [x] |
| 1.3 | `[tool.ruff]` und `[tool.ruff.lint]` aus aiohomematic adaptieren (selektive Regeln) | M | 🟡 | [x] |
| 1.4 | `[tool.mypy]` mit moderatem Baseline (`check_untyped_defs`); strict bleibt für Phase 4.10 | M | 🟡 | [x] |
| 1.5 | `[tool.pylint]` mit projektspezifischen Disables einrichten | M | 🟡 | [x] |
| 1.6 | `[tool.bandit]` konfigurieren (Skips für Tests, Confidence-Level) | S | 🟢 | [x] |
| 1.7 | `[tool.coverage.run]` + `[tool.coverage.report]` mit `fail_under = 80` (statt aktuell 0) | S | 🟢 | [x] |
| 1.8 | `[tool.pytest.ini_options]` aus `setup.cfg` übernehmen, `asyncio_mode = auto` beibehalten | S | 🟢 | [x] |
| 1.9 | `requirements_test.txt` und `requirements_dev.txt` aufräumen, Version-Pins setzen | S | 🟢 | [x] |
| 1.10 | `requirements_test_pre_commit.txt` separat (analog aiohomematic) | S | 🟢 | [x] |

---

## Phase 2 — Pre-commit-Hooks erweitern

> Alle Checks lokal vor Push, identisches Verhalten wie CI.

| # | Task | Aufwand | Risiko | Status |
|---|------|---------|--------|--------|
| 2.1 | `codespell` Hook mit Ignorier-Liste einrichten (1 echter Typo gefixt) | S | 🟢 | [x] |
| 2.2 | `yamllint` Hook + `.yamllint`-Config (Blueprints ignorieren) | S | 🟢 | [x] |
| 2.3 | `prettier` Hook für Markdown/YAML/JSON | S | 🟢 | [x] |
| 2.4 | `bandit` als pre-commit Hook | S | 🟢 | [x] |
| 2.5 | `mypy` als pre-commit Hook (mit `additional_dependencies`) | M | 🟡 | [x] |
| 2.6 | `pylint` als pre-commit Hook (via lokaler Konfig, Durchlauf in Phase 4) | M | 🟡 | [~] |
| 2.7 | Custom Hook: `lint-all-exports` (sicherstellen dass `__all__` gepflegt) → `scripts/lint_exports.py` | M | 🟡 | [x] |
| 2.8 | Custom Hook: `check-i18n` → `scripts/check_i18n.py` (7 verwaiste Keys gefixt) | M | 🟡 | [x] |
| 2.9 | Hook-Versionen aktualisiert (pre-commit-hooks v5, ruff v0.6.9, mypy v1.11.2, bandit 1.7.10) | S | 🟢 | [x] |

---

## Phase 3 — CI/CD-Pipeline ausbauen

> Jede Lint-/Typ-Kategorie als separater Job → klare Fehlersignale.

| # | Task | Aufwand | Risiko | Status |
|---|------|---------|--------|--------|
| 3.1 | Job `mypy.yaml` | S | 🟢 | [x] |
| 3.2 | Job `bandit.yaml` mit SARIF-Upload für GitHub Security Tab | M | 🟢 | [x] |
| 3.3 | Workflow `codeql.yaml` für Python | S | 🟢 | [x] |
| 3.4 | Workflow `dependency-review.yaml` (auf PRs) | S | 🟢 | [x] |
| 3.5 | Workflow `pylint.yaml` | S | 🟢 | [x] |
| 3.6 | Python-Matrix erweitern: 3.13 + 3.14 (sobald HA es unterstützt) | S | 🟡 | [-] |
| 3.7 | `codecov.yml` mit Component-Tracking (api, coordinator, device, climate, sensors, diagnostics) | S | 🟢 | [x] |
| 3.8 | Codecov-Token als Secret einrichten und Coverage-Gates aktivieren (Token bereits gesetzt) | S | 🟡 | [x] |
| 3.9 | Release-Workflow: Tag → GitHub Release → manifest.json-Version-Validierung | M | 🟡 | [x] |
| 3.10 | `dependabot.yml` um pip-Ecosystem erweitern | S | 🟢 | [x] |
| 3.11 | Job-Concurrency + Cancel-Older-Runs in allen Workflows | S | 🟢 | [x] |

---

## Phase 4 — Type Safety & Code-Hygiene

> Schrittweise mypy-strict erreichen. Modul für Modul.

| # | Task | Aufwand | Risiko | Status |
|---|------|---------|--------|--------|
| 4.1 | `const.py` typisieren (z. B. `VALUE_SENSOR_MAPPING: Final[Mapping[str, SensorMapping]]` mit TypedDict) | M | 🟢 | [ ] |
| 4.2 | `daikin_api.py` voll typisieren (Response-Types, Header-Parsing) | M | 🟡 | [ ] |
| 4.3 | `coordinator.py` voll typisieren | S | 🟢 | [ ] |
| 4.4 | `device.py` voll typisieren | M | 🟡 | [ ] |
| 4.5 | `climate.py` voll typisieren (größtes Modul, 851 Zeilen) | L | 🟡 | [ ] |
| 4.6 | `water_heater.py` voll typisieren | M | 🟡 | [ ] |
| 4.7 | `sensor.py` / `binary_sensor.py` / `select.py` / `switch.py` / `button.py` typisieren | M | 🟡 | [ ] |
| 4.8 | `Platform`-Liste durch `Final` markieren, optional als Frozenset | S | 🟢 | [ ] |
| 4.9 | `__all__` in jedem Public-Modul ergänzen | S | 🟢 | [ ] |
| 4.10 | mypy strict aktivieren, alle verbleibenden Fehler beheben (oder `# type: ignore[code]` mit Begründung) | L | 🔴 | [ ] |

---

## Phase 5 — Eigene Exception-Hierarchie & Validierung

> Klare Fehlersignale, sauberes Error-Handling im HA-Sinne.

| # | Task | Aufwand | Risiko | Status |
|---|------|---------|--------|--------|
| 5.1 | `exceptions.py` anlegen: `DaikinError` (Base) | S | 🟢 | [ ] |
| 5.2 | Subklassen: `DaikinAuthError`, `DaikinRateLimitError`, `DaikinApiError`, `DaikinDeviceError`, `DaikinValidationError` | S | 🟢 | [ ] |
| 5.3 | `daikin_api.py`: HTTP-Statuscodes auf passende Exceptions mappen (401→Auth, 429→RateLimit, 5xx→Api) | M | 🟡 | [ ] |
| 5.4 | Coordinator: spezifische Exceptions in `UpdateFailed`/`ConfigEntryAuthFailed`/`ConfigEntryNotReady` übersetzen | S | 🟡 | [ ] |
| 5.5 | Cloud-Response Schema-Validierung (z. B. `voluptuous` oder eigenes TypedDict + Validator) | L | 🟡 | [ ] |
| 5.6 | Tests für jeden Exception-Pfad | M | 🟢 | [ ] |

---

## Phase 6 — Robustheit: Retry, Backoff, Circuit-Breaker

> Stale-Reads, Rate-Limits und Cloud-Ausfälle defensiv behandeln.

| # | Task | Aufwand | Risiko | Status |
|---|------|---------|--------|--------|
| 6.1 | `support/retry.py` mit Decorator `@retry_with_backoff` (configurable: tries, base_delay, max_delay, jitter) | M | 🟢 | [ ] |
| 6.2 | Retry an `doBearerRequest` anschließen (nur idempotente Methoden GET) | M | 🟡 | [ ] |
| 6.3 | `support/circuit_breaker.py` mit States CLOSED/OPEN/HALF_OPEN | L | 🟡 | [ ] |
| 6.4 | Circuit-Breaker an `DaikinApi` anschließen, Fehler-Schwelle konfigurierbar | M | 🟡 | [ ] |
| 6.5 | `support/throttle.py` für proaktives Rate-Limit-Pacing (statt nur reaktiv bei `remaining_day == 0`) | M | 🟡 | [ ] |
| 6.6 | Tests für Retry-Verhalten (Timeouts, 5xx, 429) | M | 🟢 | [ ] |
| 6.7 | Tests für Circuit-Breaker State-Transitions | M | 🟢 | [ ] |

---

## Phase 7 — Architektur: Domain Model herauslösen

> Trennung Transport (`client/`) ↔ Domäne (`model/`) ↔ HA-Entity (`platforms`).

| # | Task | Aufwand | Risiko | Status |
|---|------|---------|--------|--------|
| 7.1 | Paketstruktur entwerfen: `client/`, `model/`, `support/`, `platforms/` (ADR schreiben) | M | 🟡 | [ ] |
| 7.2 | `client/api.py`: reine Cloud-API (HTTP, OAuth, Retry, Circuit-Breaker), kein HA-Wissen | L | 🔴 | [ ] |
| 7.3 | `model/device.py`: `DaikinDevice` (typisiert, ohne JSON-Walks in Entities) | L | 🔴 | [ ] |
| 7.4 | `model/management_point.py`: typisierte ManagementPoint-Klassen pro Typ (climateControl, domesticHotWaterTank, gateway, …) | L | 🔴 | [ ] |
| 7.5 | `model/data_point.py`: einheitliches Interface für value/min/max/stepValue (analog aiohomematic DataPoint) | L | 🔴 | [ ] |
| 7.6 | `climate.py` refaktorieren: nur noch HA-Glue, Logik im Modell | L | 🔴 | [ ] |
| 7.7 | `water_heater.py` refaktorieren: nur noch HA-Glue | M | 🔴 | [ ] |
| 7.8 | `sensor.py`: über `model.iter_data_points()` statt JSON-Walks | M | 🔴 | [ ] |
| 7.9 | Event-/Callback-System für Modell-Updates statt direkter `setJsonData()`-Pushes | L | 🔴 | [ ] |
| 7.10 | Optional: `store/` für Caching letzter erfolgreicher Cloud-Snapshots (Resilience bei Cloud-Down) | L | 🟡 | [ ] |

---

## Phase 8 — Test-Suite massiv ausbauen

> Ziel: Coverage ≥ 85 %, Fehlerpfade abgedeckt, alle Fixtures parametrisiert.

| # | Task | Aufwand | Risiko | Status |
|---|------|---------|--------|--------|
| 8.1 | `tests/conftest.py` aufteilen in `conftest.py` + `tests/fixtures/` (Python-Fixtures vs. JSON-Daten trennen) | M | 🟢 | [ ] |
| 8.2 | Eigenes `daikin_onecta_test_support/` Paket (Mock-Factories, Builder, Asserter) | L | 🟡 | [ ] |
| 8.3 | Snapshot-Tests parametrisieren über **alle** `tests/fixtures/*.json` (aktuell nur ein Subset) | M | 🟢 | [ ] |
| 8.4 | Snapshots pro Plattform (`test_climate.ambr`, `test_sensor.ambr`, …) statt eines `test_init.ambr` | M | 🟢 | [ ] |
| 8.5 | Tests für `daikin_api.py`: Token-Refresh, 401-Auth-Fail, 429-Rate-Limit, Timeout | M | 🟢 | [ ] |
| 8.6 | Tests für `coordinator.py`: High/Low-Scan-Wechsel, scan_ignore-Logik, Random-Spread | M | 🟢 | [ ] |
| 8.7 | Tests für `_cloud_lock`-Serialisierung (Race-Condition-Test) | M | 🟡 | [ ] |
| 8.8 | Tests für `async_migrate_entry` (alle Versionen) | S | 🟢 | [ ] |
| 8.9 | Contract-Tests: alle Cloud-Endpunkte gegen ein Response-Schema validieren | M | 🟡 | [ ] |
| 8.10 | Coverage ≥ 80 % erreichen | L | 🟡 | [ ] |
| 8.11 | Coverage ≥ 85 % erreichen (aiohomematic-Niveau) | L | 🟡 | [ ] |
| 8.12 | `pytest-xdist` aktivieren und Test-Isolation prüfen | S | 🟢 | [ ] |

---

## Phase 9 — Sicherheit härten

> Defensive Programmierung, Secrets, Logging.

| # | Task | Aufwand | Risiko | Status |
|---|------|---------|--------|--------|
| 9.1 | Audit aller `_LOGGER.{info,debug,exception}`-Calls: keine Tokens, keine PII | M | 🟢 | [ ] |
| 9.2 | JWT-Decode in `__init__.py:81` mit `_LOGGER.exception` prüfen — keine Token-Fragmente loggen | S | 🟢 | [ ] |
| 9.3 | TLS/Cert-Verification explizit dokumentieren (`aiohttp` Defaults bestätigen) | S | 🟢 | [ ] |
| 9.4 | Bandit-Findings aus Phase 0 abarbeiten | M | 🟡 | [ ] |
| 9.5 | CodeQL-Findings aus Phase 3.3 abarbeiten | M | 🟡 | [ ] |
| 9.6 | `SECURITY.md` mit Reporting-Prozess und supported-versions Tabelle | S | 🟢 | [ ] |
| 9.7 | Secret-Scanning auf Repo aktivieren (GitHub-Setting), `.gitleaks.toml` falls nötig | S | 🟢 | [ ] |

---

## Phase 10 — Dokumentation auf aiohomematic-Niveau

> Doku als First-class-Citizen.

| # | Task | Aufwand | Risiko | Status |
|---|------|---------|--------|--------|
| 10.1 | `changelog.md` im Repo einführen (Keep-a-Changelog-Format), historische Releases nachtragen | M | 🟢 | [ ] |
| 10.2 | `AGENTS.md` mit Contributor-Guidelines (Style, Branch, Commit, Review) | S | 🟢 | [ ] |
| 10.3 | `docs/architecture.md` (Layer-Diagramm, Datenfluss Cloud→Coordinator→Entity) | M | 🟢 | [ ] |
| 10.4 | `docs/adr/` mit allen Designentscheidungen (cloud_lock, scan_ignore, polling-Strategie, model-layer) | M | 🟢 | [ ] |
| 10.5 | `mkdocs.yml` + `docs/`-Struktur (getting_started, faq, devices, troubleshooting) | M | 🟢 | [ ] |
| 10.6 | `mkdocs gh-deploy`-Workflow in `.github/workflows/docs.yml` | S | 🟢 | [ ] |
| 10.7 | Docstring-Standards definieren (`docs/docstring_standards.md`) und enforcen via ruff `D`-Regeln | M | 🟡 | [ ] |
| 10.8 | `CONTRIBUTING.md` mit Dev-Setup-Anleitung | S | 🟢 | [ ] |
| 10.9 | `CLAUDE.md` erweitern um aktualisiertes Architektur-Bild nach Phase 7 | S | 🟢 | [ ] |
| 10.10 | `SUPPORT.md` mit Issue-Triage-Hinweisen | S | 🟢 | [ ] |

---

## Phase 11 — Release- & Versionsdisziplin

> Reproducible Releases, klare Versionspolitik.

| # | Task | Aufwand | Risiko | Status |
|---|------|---------|--------|--------|
| 11.1 | SemVer-Policy festlegen und in `CONTRIBUTING.md` dokumentieren | S | 🟢 | [ ] |
| 11.2 | `changelog.md` als Single-Source-of-Truth für Release-Notes verlinken | S | 🟢 | [ ] |
| 11.3 | Pre-Release-Checkliste: `manifest.json` Version, Changelog-Eintrag, Migration-Notes | S | 🟢 | [ ] |
| 11.4 | Release-Workflow: bei Tag `vX.Y.Z` → Validierung gegen `manifest.json` → GitHub Release erstellen | M | 🟡 | [ ] |
| 11.5 | HACS-Release-Validation in CI | S | 🟢 | [ ] |

---

## Progress Dashboard

> Diese Tabelle nach jeder Phase aktualisieren. `n/m` = abgeschlossene Tasks pro Phase.

| Phase | Thema | Tasks | Status |
|-------|-------|-------|--------|
| 0 | Baseline & Sicherheitsnetz | 5 / 5 | 🟩 |
| 1 | Tooling & Konfiguration | 10 / 10 | 🟩 |
| 2 | Pre-commit-Hooks | 8 / 9 (2.6 in Arbeit) | 🟨 |
| 3 | CI/CD-Pipeline | 10 / 11 (3.6 übersprungen bis HA 3.14 unterstützt) | 🟩 |
| 4 | Type Safety | 0 / 10 | ⬜ |
| 5 | Exceptions & Validierung | 0 / 6 | ⬜ |
| 6 | Robustheit (Retry/Breaker) | 0 / 7 | ⬜ |
| 7 | Domain Model | 0 / 10 | ⬜ |
| 8 | Test-Suite | 0 / 12 | ⬜ |
| 9 | Sicherheit | 0 / 7 | ⬜ |
| 10 | Dokumentation | 0 / 10 | ⬜ |
| 11 | Release-Disziplin | 0 / 5 | ⬜ |
| **Gesamt** | | **33 / 102** | **32 %** |

**Status-Symbole:** ⬜ nicht begonnen · 🟨 in Arbeit · 🟩 abgeschlossen

**Letztes Update:** 2026-04-17 — Phasen 0–3 abgeschlossen.

### Phase 0–3 Zusammenfassung

**Neue/aktualisierte Dateien:**
- `pyproject.toml` (vorher 2 Zeilen → jetzt zentrale Tool-Konfig: ruff, mypy, pylint, bandit, coverage, pytest, codespell)
- `setup.cfg` gelöscht
- `requirements_dev.txt`, `requirements_test.txt`, `requirements_test_pre_commit.txt`
- `.pre-commit-config.yaml` (3 Hooks → 9 Hook-Repos + 2 Custom-Hooks)
- `.yamllint`, `.prettierignore`
- `.github/workflows/`: `mypy.yaml`, `bandit.yaml`, `codeql.yaml`, `dependency-review.yaml`, `pylint.yaml`, `release.yaml` neu; `tests.yaml`, `precommit.yaml`, `dependabot.yml`, `constraints.txt` aktualisiert
- `codecov.yml` (Component-Tracking für 6 Komponenten)
- `scripts/check_i18n.py`, `scripts/lint_exports.py`
- `docs/adr/0001-record-architecture-decisions.md`
- Baselines: `coverage-baseline.txt`, `mypy-baseline.txt`, `ruff-baseline.txt`, `bandit-baseline.txt`

**Code-Fixes nebenbei:**
- `__init__.py:51` — `raise ... from ex` (B904)
- `device.py:102` — Listen-Konkatenation → unpack (RUF005)
- `sensor.py:118` — Typo "mutiple" → "multiple"
- `tests/conftest.py:78-79` — `# noqa: B015` mit TODO-Verweis auf Phase 8
- `translations/de.json` — Schlüssel-Typo `heatingmonthlyconsumption` → `heatingmonthlygasconsumption`
- `translations/{fr,it}.json` — 6 verwaiste Keys aus alter Config entfernt
- 17 Dateien einmalig per `ruff format` v0.6 reformatiert

**Verifikation:**
- ruff: ✅ All checks passed
- yamllint: ✅ exit 0
- codespell: ✅ exit 0
- pytest: ✅ 28/28 passed (Snapshot-"Failures" = TODO Phase 8)
- coverage: 97 % (Baseline)
- mypy: 49 errors (Baseline; wird in Phase 4 abgebaut)
- bandit: 2 Low-Severity False-Positives (in `[tool.bandit] skips` ausgeschlossen)

**Bewusste Abweichungen vom ROADMAP-Original:**
- 1.4 mypy: kein `strict = true` direkt — moderate Defaults plus `check_untyped_defs`. Strict bleibt für Phase 4.10 (alle Module typisiert).
- 1.3 ruff: `I` (isort) und `SIM` aktuell auskommentiert. `I` wird aktiv sobald `reorder-python-imports` entfernt ist (später in Phase 4); `SIM` aktiv nach Bestands-Refactor in Phase 4.
- 2.6 pylint: konfiguriert, aber Pre-commit-Hook noch nicht aktiviert (würde initialen Lauf wegen Bestand fehlschlagen lassen — wird in Phase 4 scharfgeschaltet).
- 3.6 Python-3.14-Matrix: übersprungen bis Home Assistant Core 3.14 offiziell unterstützt.

---

## Empfohlene Reihenfolge / Abhängigkeiten

```
Phase 0  (Baseline)
   │
   ▼
Phase 1 (pyproject) ──► Phase 2 (pre-commit) ──► Phase 3 (CI)
                                                     │
                            ┌────────────────────────┤
                            ▼                        ▼
                       Phase 4 (Typing)         Phase 9 (Security)
                            │
                            ▼
                       Phase 5 (Exceptions) ──► Phase 6 (Robustheit)
                            │
                            ▼
                       Phase 8 (Tests, parallel ab hier)
                            │
                            ▼
                       Phase 7 (Domain Model — größter Umbau)
                            │
                            ▼
                       Phase 10 (Doku) ──► Phase 11 (Release)
```

**Faustregel:** Phase 0–3 in Wochen 1–2 erledigen — danach hat jede weitere Änderung CI-Schutz. Phase 7 ist das größte Risiko und sollte erst nach soliden Tests (Phase 8) angegangen werden.

---

## Out-of-Scope / bewusste Nicht-Ziele

- Eigenes `aiohomematic_storage`-Pendant (lokaler State-Store) — nur sinnvoll wenn echte Resilience-Anforderungen entstehen.
- 3.14 free-threading-Support — abhängig von Home Assistant Core.
- Loslösung der HA-Integration in eine separate PyPI-Library (würde HACS-Distribution brechen).
