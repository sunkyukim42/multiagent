from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.core.domain_registry import DomainRegistry
from enterprise_decision_agents.core.schemas import DomainConfigError
from tradingagents.default_config import DEFAULT_CONFIG


def read_dotenv_present_names(env_path: Path) -> set[str]:
    if not env_path.exists():
        return set()

    present_names = set()
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and value:
            present_names.add(name)
    return present_names


def build_masked_env() -> dict[str, str]:
    masked_env = {name: "present" for name, value in os.environ.items() if value}
    for name in read_dotenv_present_names(PROJECT_ROOT / ".env"):
        masked_env.setdefault(name, "present")
    return masked_env


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Domain Registry YAML configs.")
    parser.add_argument(
        "--config-dir",
        default=DEFAULT_CONFIG["domain_config_dir"],
        help="Directory containing domain YAML files.",
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Report required environment variable presence without printing values.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        registry = DomainRegistry.from_config_dir(
            args.config_dir,
            default_domain=DEFAULT_CONFIG.get("domain"),
        )
    except DomainConfigError as exc:
        print(f"Domain validation failed: {exc}", file=sys.stderr)
        return 1

    domain_names = registry.list_domains()
    print("Available domains: " + ", ".join(domain_names))

    if args.check_env:
        masked_env = build_masked_env()
        for domain_name in domain_names:
            print(f"[{domain_name}]")
            statuses = registry.check_env_status(domain_name, env=masked_env)
            if not statuses:
                print("  no required env vars")
                continue
            for status in statuses:
                print(f"  {status.to_display()}")

    print("Domain validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
