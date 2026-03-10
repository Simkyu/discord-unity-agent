"""MD 스펙 파일 파싱 및 체크리스트 상태 관리."""
from __future__ import annotations

import re
from pathlib import Path

import config

AGENT_CONTEXT_PATH = Path(config.UNITY_PROJECT_PATH) / "docs" / "agent_context.md"


def resolve_md_path(command: str) -> str | None:
    """
    Discord 명령에서 .md 파일 경로를 추출하여 절대경로로 반환.
    UNITY_PROJECT_PATH 기준 상대경로와 절대경로 모두 지원.
    경로가 실제로 존재하지 않으면 None 반환.
    """
    match = re.search(r'[\w./\-]+\.md', command)
    if not match:
        return None

    raw = match.group()
    candidate = Path(raw)

    if candidate.is_absolute() and candidate.exists():
        return str(candidate)

    relative = Path(config.UNITY_PROJECT_PATH) / raw
    if relative.exists():
        return str(relative)

    return None


def count_remaining(md_path: str) -> int:
    """미완료 항목(- [ ]) 개수 반환."""
    return Path(md_path).read_text(encoding="utf-8").count("- [ ]")


def count_total(md_path: str) -> int:
    """전체 체크리스트 항목 수 반환."""
    text = Path(md_path).read_text(encoding="utf-8")
    return text.count("- [ ]") + text.count("- [x]") + text.count("- [X]")


def has_remaining(md_path: str) -> bool:
    return count_remaining(md_path) > 0


def next_item(md_path: str) -> str | None:
    """첫 번째 미완료 항목 텍스트 반환."""
    text = Path(md_path).read_text(encoding="utf-8")
    m = re.search(r"- \[ \] (.+)", text)
    return m.group(1).strip() if m else None


def read_agent_context() -> str | None:
    """agent_context.md 내용 반환. 없으면 None."""
    if AGENT_CONTEXT_PATH.exists():
        return AGENT_CONTEXT_PATH.read_text(encoding="utf-8")
    return None
