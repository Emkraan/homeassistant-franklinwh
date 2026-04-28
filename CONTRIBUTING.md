# Contributing

Thanks for considering a contribution. This document captures the conventions this project follows so that PRs land cleanly and the codebase stays consistent over time.

---

## Reporting issues

Use the GitHub issue forms (Bug report / Feature request). Fill in **every** field — reports without versions and debug logs almost always get closed without a fix. Capture instructions are embedded in the bug-report form itself.

## Submitting changes

1. Fork the repository.
2. Create a topic branch off `main` named `<type>/<short-slug>` (see Branch naming below).
3. Make your changes following the conventions in the next sections.
4. Ensure `python -m py_compile *.py` passes locally.
5. Open a PR against `main`. Reference any related issues with `Fixes #N`.

---

## Naming conventions

This project standardizes naming on **both** the GitHub side (repository, README, releases) and the Home Assistant side (entities, devices, services). Keep them aligned when adding anything new.

### GitHub side

| Surface | Convention | Example |
|---|---|---|
| Repository name | `homeassistant-<vendor>` | `homeassistant-franklinwh` |
| Repository "About" | One sentence, sentence case, ends with a period. Includes "Home Assistant integration" verbatim for searchability. | `Home Assistant integration for FranklinWH home energy storage systems.` |
| Repository topics | Lowercase hyphenated. Always include: `home-assistant`, `hacs`, `homeassistant-integration`, plus vendor + product slugs. | `home-assistant`, `hacs`, `homeassistant-integration`, `franklinwh`, `energy-storage`, `solar` |
| Default branch | `main` | — |
| Branch names | `<type>/<short-slug>` where type ∈ `feat`, `fix`, `refactor`, `docs`, `chore` | `feat/export-limit-number`, `fix/switch-timedelta-import` |
| Release tags | Match `manifest.json` `version` exactly, no `v` prefix. | `2026.4.0` |
| Release titles | `<vendor> <product> — <version>` | `FranklinWH for Home Assistant — 2026.4.0` |
| Commit subject | Imperative, sentence case, ≤ 72 chars, no trailing period. No AI / co-author trailers. | `Add export-limit Number entity` |
| Commit body | Wrap at 72 cols. Hyphen bullet list for multi-point commits. Explain *why*, not *what*. | — |
| PR title | Same as commit subject convention. | — |
| README H1 | `<vendor> Integration for Home Assistant` | `FranklinWH Integration for Home Assistant` |
| README sections (in order) | Features → Installation → Configuration → Entities → Services → Migration → Troubleshooting → Contributing → License | — |
| README headings | Sentence case, no terminal punctuation. | `## Available entities` |

### Home Assistant side

| Surface | Convention | Example |
|---|---|---|
| Domain (`manifest.json`) | `<vendor>_<product>` snake_case. Never change after first release without a migration. | `franklin_wh` |
| Display name (`manifest.json` `name`) | Vendor brand exactly as marketed. | `FranklinWH` |
| Config-entry title | `<Display name> <gateway-id>` (gateway-id last 6+ chars suffice when shown in the UI) | `FranklinWH 100ABCDEF` |
| Device name (`DeviceInfo.name`) | Same as config-entry title. | `FranklinWH 100ABCDEF` |
| Entity friendly names | **Function only**, sentence case, no vendor prefix. Set via `translation_key` in `strings.json`, never hardcoded. HA prepends the device name automatically. | `State of charge`, `Battery use`, `Smart Circuit 1` |
| `unique_id` | `<gateway-id>_<entity-key>` — never include the prefix or display name. | `100ABCDEF_state_of_charge` |
| Translation keys | snake_case, match the entity's stable internal key. | `state_of_charge`, `battery_use`, `grid_status` |
| Service names | `<domain>.<verb>_<noun>` snake_case. | `franklin_wh.set_mode` |
| Service field names | snake_case, match the underlying API parameter where possible. | `reserve_soc`, `export_limit_kw` |
| Issue / Repairs translation keys | snake_case, descriptive. | `yaml_deprecated` |

### Adding a new entity

1. Pick a stable `key` (snake_case, e.g. `solar_voltage`).
2. Add a `translation_key` matching the key.
3. Add an entry under `entity.<platform>.<key>.name` in both `strings.json` and `translations/en.json`. Friendly name is **function only**, no vendor prefix.
4. Wire `unique_id_suffix` in the platform file to the same key. The base class produces `f"{gateway_id}_{key}"`.
5. Update the README's entity table in the same PR.

---

## Code style

- Python 3.12+ syntax (Home Assistant minimum).
- Type hints on every public function. `from __future__ import annotations` at the top of every module.
- One logger per module: `_LOGGER = logging.getLogger(__name__)`.
- Use the shared `FranklinDataUpdateCoordinator` and `FranklinBaseEntity` — do not bypass them.
- Comments explain *why*, not *what*. No multi-paragraph docstrings on internal helpers.
- Never add `# Co-Authored-By:` or AI-tool attribution to commits, comments, or docs.

## Releasing

1. Bump `version` in `manifest.json`.
2. Add a section to `CHANGELOG.md` (Breaking / Added / Fixed / Changed).
3. Commit: `Release 2026.X.Y`.
4. Tag: `git tag 2026.X.Y && git push --tags`.
5. Create a GitHub release with title `FranklinWH for Home Assistant — 2026.X.Y` and body copied from the changelog section.
6. HACS users get the update automatically once the release is published.
