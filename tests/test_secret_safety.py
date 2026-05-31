import os
from pathlib import Path
import subprocess
import sys

from enterprise_decision_agents.core.domain_registry import DomainRegistry
from tradingagents.default_config import DEFAULT_CONFIG


FAKE_SECRET = "sk-test-secret-value"


def test_env_status_does_not_expose_raw_secret(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", FAKE_SECRET)
    registry = DomainRegistry.from_config_dir(
        DEFAULT_CONFIG["domain_config_dir"],
        default_domain=DEFAULT_CONFIG["domain"],
    )

    statuses = registry.check_env_status("oil")
    display = "\n".join(status.to_display() for status in statuses)

    assert "FRED_API_KEY=present" in display
    assert FAKE_SECRET not in display
    assert FAKE_SECRET not in repr(statuses)


def test_validate_domains_check_env_masks_secret_values(monkeypatch):
    env = os.environ.copy()
    env["FRED_API_KEY"] = FAKE_SECRET
    result = subprocess.run(
        [sys.executable, "scripts/validate_domains.py", "--check-env"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert "FRED_API_KEY=present" in output
    assert FAKE_SECRET not in output


def test_dotenv_is_gitignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in {line.strip() for line in gitignore}


def test_no_forbidden_scope_modules_added():
    forbidden_terms = [
        "ragas",
        "trulens",
    ]
    task2_paths = list(Path("enterprise_decision_agents").rglob("*"))
    task2_paths += list(Path("configs").rglob("*"))
    task2_paths.append(Path("scripts/validate_domains.py"))

    for path in task2_paths:
        normalized = path.as_posix().lower()
        assert not any(term in normalized for term in forbidden_terms)
