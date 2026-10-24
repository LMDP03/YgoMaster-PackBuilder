# YgoMaster-PackBuilder

**YgoMaster-PackBuilder** is a Python companion tool for [YgoMaster](https://github.com/pixeltris/YgoMaster). It imports custom packs from [YGOPRODeck](https://ygoprodeck.com/), checks their card lists and rarities against the configured league rules, and generates the shop files needed to use those packs in YgoMaster.

It also provides commands to install, update, and uninstall the generated content without replacing YgoMaster itself. PackBuilder does **not** install YgoMaster, launch its server, or configure PvP networking.

## Features

- Import custom packs defined on YGOPRODeck.
- Resolve card identifiers using the `YdkIds.txt` supplied with an existing YgoMaster installation.
- Validate pack sizes, rarity distributions, and relationships between main and mini-packs.
- Generate YgoMaster shop entries and opening probabilities.
- Preserve stable pack IDs between builds.
- Install and uninstall the generated files, keeping local backup and restoration information.

The supplied configuration currently defines a league with **3 players and 13 packs**. Other configurations can be created within the rules supported by the project.

## Requirements

Before starting, you need:

- **Python 3.11 or newer** (Python 3.12 is a suitable choice).
- **Git** to clone the repository.
- An **existing YgoMaster installation** containing `Data/Shop.json` and `Data/YdkIds.txt`.
- An internet connection when importing packs from YGOPRODeck.

PackBuilder's Python dependencies are declared in the repository's root `pyproject.toml` and installed automatically with `pip`: `PyYAML` and `requests`.

> **Virtual environments are local.** The repository does **not** contain a Python virtual environment or installed dependencies. After cloning it, **each user creates their own** `.venv` on their own machine. `.venv/` is excluded by `.gitignore` and must **not** be committed or uploaded. The examples below create `.venv` inside the local working directory only for convenience; it can also live elsewhere.

> On Linux, **PackBuilder runs natively with Python**. Wine may be needed for the YgoMaster game/client itself, but not for this tool.

## Installation

The same Git repository is used on every operating system. Choose the instructions for your machine; the virtual environment and dependencies are installed separately on each device.

If the repository is private, make sure your Git credentials or SSH key have access before cloning.

### Windows (PowerShell)

Install [Python](https://www.python.org/downloads/windows/) and [Git](https://git-scm.com/downloads/win), then open a new PowerShell window. For example, on systems with `winget`:

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
```

Clone the repository and create a **local**, untracked virtual environment:

```powershell
git clone https://github.com/LMDP03/YgoMaster-PackBuilder.git
cd YgoMaster-PackBuilder
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

Check the installation:

```powershell
.\.venv\Scripts\ygomaster-packbuilder.exe --help
```

The commands above call the virtual environment directly, so PowerShell script activation is not required. If the CLI executable is not available yet, use `.\.venv\Scripts\python.exe -m ygomaster_packbuilder.cli --help`.

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip

git clone https://github.com/LMDP03/YgoMaster-PackBuilder.git
cd YgoMaster-PackBuilder
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/ygomaster-packbuilder --help
```

Check that the installed `python3` is version 3.11 or newer. If not, install a supported interpreter and use it to create `.venv`.

### Fedora

```bash
sudo dnf install -y git python3 python3-pip

git clone https://github.com/LMDP03/YgoMaster-PackBuilder.git
cd YgoMaster-PackBuilder
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/ygomaster-packbuilder --help
```

### Arch Linux

```bash
sudo pacman -Syu --needed git python python-pip

git clone https://github.com/LMDP03/YgoMaster-PackBuilder.git
cd YgoMaster-PackBuilder
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/ygomaster-packbuilder --help
```

## Usage

The `ygomaster-packbuilder` executable requires the `[project.scripts]` entry in the **root** `pyproject.toml`. If you are using a revision without that entry, invoke the CLI with your environment’s Python and `-m ygomaster_packbuilder.cli` instead.

Run these commands from the **PackBuilder repository root**. The `--ygomaster-dir` argument is the path to the **YgoMaster root folder** (the one containing `Data/`), not to `Data/`, `Shop/`, or an executable. You do not need to specify `YdkIds.txt` separately; the tool locates it under `Data/`.

### Activate the virtual environment

The `.venv` directory is created **locally during installation** and does not need to be recreated for each use. Open a terminal in the PackBuilder repository root and activate it whenever you start a new terminal session.

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux (Ubuntu/Debian, Fedora, Arch):**

```bash
source .venv/bin/activate
```

With the environment active, the `ygomaster-packbuilder` command is available directly:

### Build without installing

```bash
ygomaster-packbuilder build --ygomaster-dir "/path/to/YgoMaster"
```

This imports the configured packs, runs validation, and generates the files under `build/`. **Run this command first**, before modifying your YgoMaster installation.

### Build and install

```bash
ygomaster-packbuilder install --ygomaster-dir "/path/to/YgoMaster"
```

This runs the same build and validation steps, then installs the generated files into YgoMaster. Stop the relevant YgoMaster process before installing and restart it afterward.

### Uninstall

```bash
ygomaster-packbuilder uninstall --ygomaster-dir "/path/to/YgoMaster"
```

This removes PackBuilder-managed files and restores the previous shop setting using the installation state saved on that machine. If managed files have been modified independently, the uninstaller may refuse to overwrite them.

For a Windows path, for example:

```powershell
ygomaster-packbuilder build --ygomaster-dir "C:\Games\YgoMaster"
```

The `build` and `install` commands also accept `--project-root` if you run them from outside the cloned PackBuilder directory. To see all arguments, use `ygomaster-packbuilder --help` or `<command> --help`.

### Deactivate the virtual environment

When you have finished using PackBuilder, run the following command on **Windows and Linux**:

```bash
deactivate
```

The virtual environment stays on your machine; `deactivate` only exits it for the current terminal session. You will need to activate it again in a new session.

## Project files

The main user-editable configuration lives in:

```text
config/
├── project.yaml          # Players, packs, and YGOPRODeck references
├── policies.yaml         # Pack-opening probabilities and guarantees
└── rarity_mapping.yaml   # Source rarity conversion
```

Successful builds create:

```text
build/
├── Shop/ygomaster-packbuilder.json
├── ShopPackOdds/ygomaster-packbuilder.json
└── ShopSettings.patch.json

state/ygomaster_ids.json
```

**What goes into Git:**

| Item | Commit to the repository? |
| --- | --- |
| Python source code, `pyproject.toml`, configs, docs | **Yes** |
| `state/ygomaster_ids.json` | **Yes** — keep pack IDs consistent across devices |
| `.venv/` and installed Python packages | **No** — generated locally on each machine |
| `build/` generated files | **No** — regenerated as needed |
| `<YgoMaster>/.ygomaster-packbuilder/` | **No** — per-installation state and backups |

The project `.gitignore` already excludes `.venv/` and generated build files. The stable ID registry is intentionally tracked; commit it after a successful build that assigns new pack IDs.

## Notes and limitations

- Pack imports depend on YGOPRODeck's custom-pack endpoint, which can be slow to reflect recent changes. **PackBuilder does not cache API responses.**
- Cards without a valid mapping in YgoMaster's `YdkIds.txt`, or packs that violate the configured rules, stop the build with an error.
- PackBuilder generates shop data; it does not add new card artwork/assets or configure multiplayer connectivity.
- Test the generated content and opening behavior with the target YgoMaster version before using it in a live league.

## Technical documentation

See [docs/](docs/README.md) for the project architecture, data models, rules, validation, sources, export format, registry, workflow, and installer implementation.
