# Workflow, CLI and testing

## 1. Public orchestration APIs

The central module is `src/ygomaster_packbuilder/workflow.py`. The two main entry points are:

```python
build_project(project_root, ygomaster_dir, *, ygoprodeck_client=None) -> BuildWorkflowResult
build_and_install_project(project_root, ygomaster_dir, *, ygoprodeck_client=None) -> InstallWorkflowResult
```

`build_project()` **requires a YgoMaster root even when not installing**, because it reads `<YgoMaster>/Data/YdkIds.txt` and `<YgoMaster>/Data/CardList.json`. `ygoprodeck_client` is optional and allows deterministic fake-client tests. If not supplied, `assemble_project_definition()` creates a real `YgoProDeckClient`.

`BuildWorkflowResult` holds `project: ProjectDefinition`, `pack_ids: dict[str,int]`, `artifacts: YgoMasterBuildArtifacts`, and `paths: WorkflowPaths`. `InstallWorkflowResult` holds the build result and `YgoMasterInstallResult`.

`uninstall_ygomaster_build(ygomaster_dir)` is in the installer package, not in workflow.py, because removing managed files does not require fetching/assembling packs.

## 2. Paths

`resolve_workflow_paths()` resolves absolute paths and checks both roots exist, and that `Data/YdkIds.txt` and `Data/CardList.json` exist. It derives:

| Field | File/directory relative to root |
| --- | --- |
| `manifest` | `<project_root>/config/project.yaml` |
| `policies` | `<project_root>/config/policies.yaml` |
| `rarity_mapping` | `<project_root>/config/rarity_mapping.yaml` |
| `ydk_mapping` | `<ygomaster_dir>/Data/YdkIds.txt` |
| `card_catalog` | `<ygomaster_dir>/Data/CardList.json` |
| `id_registry` | `<project_root>/state/ygomaster_ids.json` |
| `build_dir` | `<project_root>/build` |

The install destination is inferred by `installer/ygomaster.py` from `<ygomaster_dir>/Data/`; these are intentionally not separate user-configurable paths.

## 3. `build_project()` implementation sequence

1. Resolve all paths; read manifest and policy YAML.
2. Validate manifest, policies and cross-policy references; stop on error before fetching external packs.
3. Read rarity, YDK mapping and YgoMaster card catalog files.
4. Assemble project by fetching/parsing YGOPRODeck packs and mapping card rarities/IDs.
5. Domain-validate full project, then verify resolved Master Duel IDs against `CardList.json`; stop on errors before registry allocation/build.
6. Load persistent registry; allocate stable IDs for any new pack keys **in memory**.
7. Write and validate artifacts in `TemporaryDirectory(prefix=".ygomaster-packbuilder-", dir=project_root)`.
8. Write and validate final `build/` artifacts.
9. Save `state/ygomaster_ids.json` only after final build validation succeeds.
10. Return the project, assigned IDs, artifact paths and resolved paths.

`build_and_install_project()` invokes `build_project()` then `install_ygomaster_build()`; this second step validates the build again, reads/patches the YgoMaster target and persists local installation state.

**Side-effect boundaries:** configuration/domain failures do not write new build/registry files. A failure after final file writes may leave partial build data, and an installation failure occurs **after** the successful build/registry save. This design is not a full cross-file transaction.

## 4. CLI

The terminal interface is `src/ygomaster_packbuilder/cli.py`, whose `main(argv: list[str] | None = None) -> int` uses `argparse` with required subcommands. The executable is registered in **the repository-root** `pyproject.toml`:

```toml
[project.scripts]
ygomaster-packbuilder = "ygomaster_packbuilder.cli:main"
```

If this entry is present only in a misplaced `src/ygomaster_packbuilder/pyproject.toml`, `pip install -e .` from the repository root will **not** install the CLI command. Keep one authoritative project metadata file at the repository root.

| Command | Required args | Optional args | Function |
| --- | --- | --- | --- |
| `build` | `--ygomaster-dir` | `--project-root` (defaults to CWD) | `build_project()` |
| `install` | `--ygomaster-dir` | `--project-root` (defaults to CWD) | `build_and_install_project()` |
| `uninstall` | `--ygomaster-dir` | none | `uninstall_ygomaster_build()` |

Example (inside an activated virtual environment and repository root):

```bash
ygomaster-packbuilder build --ygomaster-dir "/path/to/YgoMaster"
ygomaster-packbuilder install --ygomaster-dir "/path/to/YgoMaster"
ygomaster-packbuilder uninstall --ygomaster-dir "/path/to/YgoMaster"
```

CLI `main()` returns `0` on success and `1` for captured domain/workflow/filesystem/source/configuration exceptions, printing `ERROR: ...` to stderr. `argparse` handles usage errors separately (normally exit code 2). The CLI prints project summary/IDs and modified paths but is **not** a structured JSON-report interface.

The CLI can also be launched as `python -m ygomaster_packbuilder.cli ...` if the venv's executable is not on PATH.

## 5. Dependencies and packaging

`pyproject.toml` declares `requires-python = ">=3.11"`, `PyYAML>=6.0`, `requests>=2.32`, and setuptools build backend. The project uses a `src/` layout; `pip install -e .` from a Python virtual environment installs the package and script entry point. There is no dependency on Jupyter for normal operation (Jupyter is used for manual testing only).

For Windows, Linux Ubuntu/Debian, Fedora and Arch setup instructions, see the root [README](../README.md). The native Python builder runs on Linux regardless of whether the YgoMaster game/server runtime uses Wine.

## 6. Test organization and limitations

`tests/` contains manually run `.ipynb` notebooks for manifest, policies, mapping, YGOPRODeck parsing/conversion, pack/project assembly, validation, registry, exporters, writer, installer/uninstaller and the end-to-end workflow. They use synthetic data and temporary directories to avoid side effects on a real game installation; an optional live notebook can fetch from YGOPRODeck.

There is no packaged `pytest` test suite, no automated CI and no local YGOPRODeck response cache. Passing offline tests shows Python-layer consistency, not real-world source freshness or that shop UI, x10 guarantees and pity behave correctly on the user's specific YgoMaster build.

## 7. Operational checklist

1. Ensure YgoMaster's `Data/YdkIds.txt` is appropriate for the target installation.
2. Make sure current YGOPRODeck data satisfies the pack rules and rarity mappings.
3. Run `build` and inspect `build/` output; resolve any domain failures.
4. Commit updates to `state/ygomaster_ids.json` so pack IDs stay stable across machines.
5. Stop the relevant YgoMaster runtime, run `install`, then restart it.
6. Verify packs, costs, rarity behavior and x10/pity behavior in the running game before treating the setup as fully deployed.
7. Use `uninstall` only against the same target whose local install state should be restored.

**Development roadmap rather than existing behavior:** cross-mod collision scanning, a transaction/rollback journal, configurable prices, custom artwork and runtime integration verification could be added later. They should not be described as already implemented.
