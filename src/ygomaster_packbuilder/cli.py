import argparse
import sys
from pathlib import Path

import requests
import yaml

from ygomaster_packbuilder.installer import YgoMasterInstallError, uninstall_ygomaster_build
from ygomaster_packbuilder.workflow import (
    BuildWorkflowResult,
    WorkflowError,
    build_and_install_project,
    build_project,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and install custom YgoMaster packs.")
    commands = parser.add_subparsers(dest="command", required=True)

    for name, description in (
        ("build", "Generate and validate the YgoMaster build without installing it."),
        ("install", "Build, validate, and install the custom packs into YgoMaster."),
    ):
        command = commands.add_parser(name, help=description)
        command.add_argument("--project-root", type=Path, default=Path.cwd(), help="PackBuilder root (default: current directory).")
        command.add_argument("--ygomaster-dir", type=Path, required=True, help="YgoMaster root directory.")

    uninstall = commands.add_parser("uninstall", help="Remove PackBuilder packs and restore the previous YgoMaster settings.")
    uninstall.add_argument("--ygomaster-dir", type=Path, required=True, help="YgoMaster root directory.")
    return parser


def _print_build(result: BuildWorkflowResult) -> None:
    print(f"Project: {result.project.name}")
    print(f"Players: {len(result.project.players)} | Packs: {len(result.project.packs)}")
    for pack in result.project.packs:
        print(f"  {result.pack_ids[pack.key]} | {pack.key} | {len(pack.cards)} cards")
    print(f"Build directory: {result.artifacts.root}")
    print(f"ID registry: {result.paths.id_registry}")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "build":
            _print_build(build_project(args.project_root, args.ygomaster_dir))
        elif args.command == "install":
            result = build_and_install_project(args.project_root, args.ygomaster_dir)
            _print_build(result.build)
            print(f"Installation completed: {len(result.installation.changed_files)} file(s) changed.")
            for path in result.installation.changed_files:
                print(f"  Updated: {path}")
            if not result.installation.changed_files:
                print("YgoMaster is already up to date.")
        else:
            result = uninstall_ygomaster_build(args.ygomaster_dir)
            print(f"Uninstall completed: {len(result.changed_files)} file(s) changed.")
            for path in result.removed_files:
                print(f"  Removed: {path}")
            for path in result.restored_files:
                print(f"  Restored: {path}")
        return 0
    except (WorkflowError, YgoMasterInstallError, OSError, ValueError, KeyError,
            requests.RequestException, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
