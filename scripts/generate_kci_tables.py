from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.research.research_pack import generate_kci_tables


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Task 9 KCI-style Markdown tables.")
    parser.add_argument("--evaluation-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--table-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        outputs = generate_kci_tables(
            evaluation_dir=args.evaluation_dir,
            output_dir=args.output_dir,
            table_id=args.table_id,
        )
    except Exception as exc:
        print(f"KCI table generation failed: {exc}", file=sys.stderr)
        return 1

    print(f"KCITables: {args.output_dir}")
    print(f"Summary: table={outputs['kci_tables']} manifest={outputs['artifact_manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
