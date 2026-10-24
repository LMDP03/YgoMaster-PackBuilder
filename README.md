# YgoMaster-PackBuilder

**YgoMaster-PackBuilder** imports custom Yu-Gi-Oh! packs from [YGOPRODeck](https://ygoprodeck.com/), validates their contents against a configurable league structure, and generates shop data for [pixeltris/YgoMaster](https://github.com/pixeltris/YgoMaster). It can install the generated packs into an existing YgoMaster installation and safely uninstall its managed files.

The builder is a **companion tool**, not a replacement for YgoMaster or the Master Duel client. It runs in Python on Windows or Linux; it does not configure game servers, VPNs, accounts or PvP connectivity.

## What it does

- Imports YGOPRODeck custom packs and their card rarities.
- Maps YDK/passcode IDs to Master Duel internal IDs using the existing YgoMaster `Data/YdkIds.txt`.
- Applies pack-type-specific rarity mappings and checks league rules (pack sizes, rarity counts, mini-pack subsets and disjointness).
- Generates YgoMaster-compatible `Shop` and `ShopPackOdds` JSON with configurable opening odds.
- Keeps numeric pack IDs stable across builds through a versioned registry.
- Installs, updates or removes its own pack files, retaining local installation state and restoring the prior `PerPackRarities` setting when uninstalling.

The checked-in configuration currently describes **3 players, 13 packs** (3 main packs, 9 mini-packs, 1 shared staples pack). Configuration files can be edited for another league; the current validation rules remain specific to this pack structure.

## Requirements

- **Python 3.11 or newer**, Git and an internet connection for fetching packs from YGOPRODeck.
- An existing, compatible **YgoMaster installation** with `Data/Shop.json` and `Data/YdkIds.txt`.
- Python dependencies installed automatically from `pyproject.toml`: `PyYAML>=6.0` and `requests>=2.32`.

> **Important:** Install this repository and run the CLI using your native Python environment. On Linux, the builder itself does **not** require Wine; how the YgoMaster game/server is run is a separate concern.

## Installation

In each case, clone the repository, create an isolated Python virtual environment, and install the package in editable mode. Commands assume you are inside the cloned repository. **If the GitHub repository is private, authenticate with an account that has access before cloning** (for example with a Git credential manager or SSH).

### Windows (PowerShell)

Install [Python](https://www.python.org/downloads/windows/) (3.11+) and [Git](https://git-scm.com/downloads/win). You may use Windows Package Manager:

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
```

Open a new PowerShell terminal after installing those tools:

```powershell
git clone https://github.com/LMDP03/YgoMaster-PackBuilder.git
cd YgoMaster-PackBuilder
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Run the CLI through its executable in the environment (no PowerShell execution-policy change needed):

```powershell
.\.venv\Scripts\ygomaster-packbuilder.exe --help
```

Alternatively, activate the environment with `.\.venv\Scripts\Activate.ps1` if your PowerShell policy permits it, then use `ygomaster-packbuilder` directly.

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
git clone https://github.com/LMDP03/YgoMaster-PackBuilder.git
cd YgoMaster-PackBuilder
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
ygomaster-packbuilder --help
```

If your default `python3` is older than 3.11, install/select a supported Python version before creating the environment.

### Fedora

```bash
sudo dnf install -y git python3 python3-pip
git clone https://github.com/LMDP03/YgoMaster-PackBuilder.git
cd YgoMaster-PackBuilder
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
ygomaster-packbuilder --help
```

### Arch Linux

```bash
sudo pacman -Syu --needed git python python-pip
git clone https://github.com/LMDP03/YgoMaster-PackBuilder.git
cd YgoMaster-PackBuilder
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
ygomaster-packbuilder --help
```

On Linux, reactivate the environment in a new terminal with `source .venv/bin/activate`, or call `.venv/bin/ygomaster-packbuilder` directly. The Python installation is independent of the location of YgoMaster, including installations used through Wine.

## Using the CLI

Run commands **from the PackBuilder repository root**. `--ygomaster-dir` must point to the YgoMaster directory **containing `Data/`**, not directly to `Data/`, `Shop/`, or a game executable.

**Build only — recommended first:**

```bash
ygomaster-packbuilder build --ygomaster-dir "/path/to/YgoMaster"
```

**Build, validate and install:**

```bash
ygomaster-packbuilder install --ygomaster-dir "/path/to/YgoMaster"
```

**Uninstall and restore previous settings:**

```bash
ygomaster-packbuilder uninstall --ygomaster-dir "/path/to/YgoMaster"
```

On Windows PowerShell, use the environment executable and a Windows path, for example:

```powershell
.\.venv\Scripts\ygomaster-packbuilder.exe build --ygomaster-dir "C:\Games\YgoMaster"
```

For `build` and `install`, you can explicitly select a different PackBuilder directory using `--project-root "/path/to/YgoMaster-PackBuilder"`. If the shell cannot find the installed command, `python -m ygomaster_packbuilder.cli ...` is an equivalent entry point when the virtual environment is active.

**Do a successful `build` and inspect its results before the first `install`.** Stop YgoMaster while changing its files and restart the relevant process afterwards; generating or installing JSON does not hot-reload the running game/server.

## Files and configuration

Edit `config/project.yaml`, `config/policies.yaml` and `config/rarity_mapping.yaml` to configure the packs and probabilities. YGOPRODeck updates may not immediately be reflected in its API, and the build can fail validation until its responses are updated.

Successful builds produce:

```text
build/
├── Shop/ygomaster-packbuilder.json
├── ShopPackOdds/ygomaster-packbuilder.json
└── ShopSettings.patch.json

state/ygomaster_ids.json
```

The **ID registry** is intentionally version-controlled: after the first successful build, commit changes to `state/ygomaster_ids.json` so all installations use the same numeric pack IDs. Generated `build/` files are ignored by Git. Local installation backups/state live under `<YgoMaster>/.ygomaster-packbuilder/` and should not be committed.

The current exporter does not create new card assets or `ShopPackOddsVisuals.json`. Runtime behavior, in particular opening guarantees, should be checked in the target YgoMaster version before relying on it for a live league.

## Documentation

Developer-level design, validation codes, data formats and implementation details are in [docs/](docs/README.md). This README deliberately covers setup and day-to-day use only.

## Current limitations

The YGOPRODeck custom-pack endpoint used by the source adapter is not a documented public API; its response shape, availability and update latency can change. An unmapped YDK ID blocks a build rather than being assigned a guessed Master Duel ID. Installation writes into YgoMaster's data directory; it is not a substitute for testing against an actual server/client setup.
