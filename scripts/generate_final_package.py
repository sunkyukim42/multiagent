from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.presentation.final_package_builder import build_final_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the offline Task 10 final package.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--package-id", default=None)
    parser.add_argument("--fail-fast", action="store_true", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary, manifest, outputs = build_final_package(
            config_path=args.config,
            output_dir=args.output_dir,
            package_id=args.package_id,
            fail_fast=args.fail_fast,
        )
    except Exception as exc:
        print(f"Final package generation failed: {exc}", file=sys.stderr)
        return 1

    print(f"FinalPackage: {outputs['readme'].parent}")
    print(
        "Summary: "
        f"package_id={summary.package_id} "
        f"artifacts={len(summary.artifacts)} "
        f"manifest={outputs['artifact_manifest']} "
        f"readme={outputs['readme']}"
    )
    print(f"ConfigPackage: {manifest.get('config_package_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
