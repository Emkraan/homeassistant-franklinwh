# Changelog

All notable changes to this integration are documented here. Versions follow the upstream `franklinwh` Python package, suffixed with our own patch counter when needed.

## [2026.4.0] — 2026-04-28

### Breaking

- **YAML configuration is deprecated.** Existing `sensor:` and `switch:` platform entries are auto-imported as a config entry on first run; a Repairs-registry warning prompts removal. YAML continues to work for one release cycle.
- The integration now requires Home Assistant **2026.2** or newer (for HTTP/2 ALPN helpers).

### Added

- **UI configuration flow** — Settings → Devices & Services → Add Integration → FranklinWH. Validates credentials, auto-detects gateways, offers a picker if multiple are bound to the account.
- **Reauthentication flow** — when stored credentials stop working, HA prompts to re-enter the password without a restart.
- **Options flow** — update interval, name prefix, stale-data tolerance, and per-axis sign-flip toggles for battery / grid power.
- **Multi-gateway support** — each aGate becomes its own config entry and HA device.
- **Device grouping** — every entity registers under one `DeviceInfo` per gateway.
- **Binary sensors** — `grid_online`, `generator_enabled`.
- **Number entities** — battery reserve SoC %, grid-export limit kW (hidden when export mode is `no_export`).
- **Select entities** — operating mode (TOU / self-consumption / emergency backup), grid-export mode (solar-only / solar-and-battery / no-export).
- **Per-relay smart-circuit switches** — three independent switches instead of one ganged.
- **Service calls** — `franklin_wh.set_mode`, `franklin_wh.set_export_settings`, `franklin_wh.set_generator`.
- **Translations / strings** — full `strings.json` + `translations/en.json`.
- **Generator energy sensor** — registers correctly (it was orphaned in 2026.3.x).
- **GitHub issue forms** — structured bug-report and feature-request templates.
- `CHANGELOG.md`, `CONTRIBUTING.md`.

### Fixed

- `switch.py` no longer crashes on setup due to a missing `timedelta` import.
- Failed cloud fetches now raise `UpdateFailed` (or `ConfigEntryAuthFailed` for credential errors) instead of being silently swallowed and leaving entities in a stale `None` state.
- Stringified-default workarounds for `use_sn` and `prefix` removed.
- Global `franklinwh.HttpClientFactory` mutation moved out of per-platform setup into a one-shot install at integration setup.
- Typo and an inappropriate comment in `switch.py` removed.

### Changed

- 20 near-identical sensor classes collapsed into one description-driven `FranklinSensor` plus a tuple of `FranklinSensorEntityDescription`s.
- All entities now use `_attr_has_entity_name = True` and translation keys.
- README rewritten UI-first.
- `manifest.json`: `config_flow: true`, codeowner `@cmarko89`, fork URLs.

[2026.4.0]: https://github.com/cmarko89/homeassistant-franklinwh/releases/tag/2026.4.0
