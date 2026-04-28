<p align="center">
  <img src=".github/franklinwh.png" alt="FranklinWH" width="120" />
</p>

<h1 align="center">FranklinWH Integration for Home Assistant</h1>

<p align="center">
  Monitor and control FranklinWH aPower / aGate energy storage from Home Assistant — fully UI-configurable, multi-gateway aware, Energy-dashboard ready.
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-blue.svg?style=for-the-badge" alt="HACS Custom"></a>
  <a href="https://github.com/cmarko89/homeassistant-franklinwh/releases"><img src="https://img.shields.io/github/v/release/cmarko89/homeassistant-franklinwh?style=for-the-badge" alt="Latest release"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-2026.2%2B-41BDF5?style=for-the-badge&logo=home-assistant&logoColor=white" alt="HA 2026.2+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT%20%2F%20Apache--2.0-green?style=for-the-badge" alt="License"></a>
</p>

> ⚠️ This project is unofficial and not affiliated with FranklinWH.

---

## Table of contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entities](#entities)
- [Services](#services)
- [Migration from YAML](#migration-from-yaml)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **UI configuration** — add the integration from Settings → Devices & Services. No YAML needed.
- **Multi-gateway aware** — accounts with more than one aGate get a picker; each gateway becomes its own device with its own entities.
- **Reauthentication flow** — when your password changes, Home Assistant prompts to re-enter it; no restart needed.
- **One device, all entities** — every sensor, switch, number, and select lives under a single FranklinWH device card.
- **Read & write** — not just monitoring. Toggle smart circuits, change operating mode, set battery reserve, change export mode and limit, enable/disable the generator.
- **Energy Dashboard ready** — kWh sensors carry the right device classes for the HA Energy panel.
- **Stale-tolerant polling** — keeps the last good reading on the dashboard during transient cloud outages instead of strobing entities to "unavailable".
- **Sign-flip toggles** — invert battery / grid sign at the entity layer (no template-sensor workaround).
- **Service calls** — `franklin_wh.set_mode`, `franklin_wh.set_export_settings`, `franklin_wh.set_generator` for use in scripts and automations.

---

## Installation

### Via HACS (recommended)

1. In Home Assistant, open **HACS → Integrations**.
2. Menu (⋮) → **Custom repositories**.
3. Add the repo URL: `https://github.com/cmarko89/homeassistant-franklinwh`
4. Category: **Integration**. Click **Add**.
5. Install **FranklinWH** from the list.
6. Restart Home Assistant.
7. **Settings → Devices & Services → Add Integration → FranklinWH** and follow the prompts.

### Manual

1. Copy this repository's contents into `<config>/custom_components/franklin_wh/`.
2. Restart Home Assistant.
3. Add the integration from the UI as above.

---

## Configuration

All configuration is done via the UI. You will need:

- The **email and password** for your FranklinWH account.
- (Optional) Your **gateway serial number** — needed only if you have multiple aGates and want to confirm which one to add.

> Find the gateway SN in the FranklinWH mobile app: **Settings → Device Info → SN**.

### Options

After setup, click **Configure** on the integration card to access:

| Option | Default | What it does |
|---|---|---|
| Entity name prefix | `FranklinWH` | Prefix used in entity friendly names |
| Update interval (seconds) | `30` | How often to poll the FranklinWH cloud (10–600s) |
| Keep last-known data when the cloud fails | `on` | Avoids dashboard strobing during transient outages |
| Flip battery-use sign | `off` | Invert sign of `battery_use` so charge/discharge match your convention |
| Flip grid-use sign | `off` | Invert sign of `grid_use` so import/export match your convention |

---

## Entities

All entities are grouped under one device per gateway.

### Sensors

| Entity | Description | Unit |
|---|---|---|
| State of charge | Battery state of charge | % |
| Battery use | Live charge/discharge power | kW |
| Battery charge | Lifetime energy charged | kWh |
| Battery discharge | Lifetime energy discharged | kWh |
| Home load | Live home power use | kW |
| Home use | Lifetime home energy | kWh |
| Grid use | Live import/export power | kW |
| Grid import | Lifetime energy imported | kWh |
| Grid export | Lifetime energy exported | kWh |
| Grid status | Enum: NORMAL / DOWN / OFF | — |
| Solar production | Live solar power | kW |
| Solar energy | Lifetime solar energy | kWh |
| Generator output | Live generator power | kW |
| Generator energy | Lifetime generator energy | kWh |
| Smart Circuit 1 / 2 load | Live load on each smart circuit | W |
| Smart Circuit 1 / 2 lifetime use | Lifetime energy per circuit | Wh |
| V2L use / export / import | Vehicle-to-Load metrics | W / Wh |

### Binary sensors

| Entity | When `on` |
|---|---|
| Grid online | Grid status is NORMAL |
| Generator enabled | Generator is currently running |

### Switches (only created if a Smart Circuit module is detected)

| Entity | Controls |
|---|---|
| Smart Circuit 1 | Relay 1 |
| Smart Circuit 2 | Relay 2 |
| V2L circuit | Relay 3 |

> ⚠️ If two circuits are physically merged at the gateway (`SwMerge`), the FranklinWH cloud will refuse mismatched commands to protect your wiring. Toggling one will return an error in that case — set both to the same value, or unmerge in the FranklinWH app.

### Number

| Entity | Range | Notes |
|---|---|---|
| Battery reserve | 0–100 % | Reserves battery SoC for the **active** operating mode |
| Grid export limit | 0–100 kW | Hidden when export mode is "no export" |

### Select

| Entity | Options |
|---|---|
| Operating mode | Time of use / Self consumption / Emergency backup |
| Grid export mode | Solar only / Solar and battery / No export |

---

## Services

### `franklin_wh.set_mode`

Change operating mode and (optionally) the SoC reserve in one call.

```yaml
service: franklin_wh.set_mode
data:
  mode: time_of_use     # or self_consumption / emergency_backup
  reserve_soc: 20       # optional, 0–100
  gateway: "100xxxx"    # optional, only needed if you have multiple gateways
```

### `franklin_wh.set_export_settings`

```yaml
service: franklin_wh.set_export_settings
data:
  export_mode: solar_and_apower   # or solar_only / no_export
  export_limit_kw: 5.0            # optional, ignored when no_export
```

### `franklin_wh.set_generator`

```yaml
service: franklin_wh.set_generator
data:
  enabled: true
```

---

## Migration from YAML

Earlier versions of this integration required `sensor:` and `switch:` blocks in `configuration.yaml`. On startup, the integration will:

1. **Auto-import** legacy YAML into a config entry,
2. Raise a **Repairs issue** prompting you to remove the YAML, and
3. Continue to honor the YAML for one release cycle.

After the import succeeds, delete the `franklin_wh` blocks from `configuration.yaml`. The UI flow is now the only supported path.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Invalid auth` during setup | Wrong email/password | Double-check; note that FranklinWH may temporarily lock the account after several failed tries |
| `Account locked` | Too many failed logins | Wait 15 minutes |
| `Cannot connect` | Cloud outage or DNS | Check `https://energy.franklinwh.com/` from the HA host |
| Entities go "unavailable" intermittently | Cloud is flaky | Make sure **Keep last-known data when the cloud fails** is enabled in options |
| Smart-circuit toggle returns `RuntimeError` | The gateway has the relays merged (`SwMerge=1`) | Toggle both relays together via the service call, or unmerge in the FranklinWH app |
| No switches appear | Gateway reports no Smart Circuit module | Confirm hardware presence in the FranklinWH app |

Enable verbose logs with:

```yaml
logger:
  logs:
    custom_components.franklin_wh: debug
    franklinwh: debug
```

---

## Contributing

Issues and pull requests welcome at <https://github.com/cmarko89/homeassistant-franklinwh>.

## License

Dual-licensed under the MIT License and the Apache License 2.0. Pick whichever you prefer.
