from __future__ import annotations

import re


ACTION_ALIASES = {
    "BUY": {"BUY", "매수", "留ㅼ닔"},
    "SELL": {"SELL", "매도", "留ㅻ룄"},
    "HOLD": {"HOLD", "보유", "관망", "蹂댁쑀"},
}

ASCII_ACTION_BOUNDARY = r"(?<![0-9A-Za-z_]){alias}(?![0-9A-Za-z_])"


def canonicalize_custom_action(action: str | None) -> str | None:
    if action is None:
        return None
    stripped = action.strip()
    if not stripped:
        return None
    normalized = re.sub(r"[^0-9A-Za-z가-힣]+", "_", stripped).strip("_")
    return normalized.upper() if normalized else None


def _matches_alias(text: str, upper_text: str, alias: str) -> bool:
    if alias.isascii():
        pattern = ASCII_ACTION_BOUNDARY.format(alias=re.escape(alias.upper()))
        return re.search(pattern, upper_text) is not None
    return alias in text


def normalize_action(raw_output: str | None) -> str | None:
    if raw_output is None:
        return None
    text = raw_output.strip()
    if not text:
        return None

    upper_text = text.upper()
    for canonical, aliases in ACTION_ALIASES.items():
        for alias in aliases:
            if _matches_alias(text, upper_text, alias):
                return canonical
    return canonicalize_custom_action(text)


def normalize_allowed_actions(actions: list[str]) -> list[str]:
    return [action for action in (canonicalize_custom_action(item) for item in actions) if action]
