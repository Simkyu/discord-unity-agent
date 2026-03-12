from __future__ import annotations

import asyncio
import datetime
import re
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_LAST_MD_FILE = Path(__file__).parent.parent / ".last_md_path"


def _load_last_md_path() -> str | None:
    if _LAST_MD_FILE.exists():
        path = _LAST_MD_FILE.read_text(encoding="utf-8").strip()
        return path if path else None
    return None


def _save_last_md_path(path: str) -> None:
    _LAST_MD_FILE.write_text(path, encoding="utf-8")

from agent.prompt import build_feedback_prompt, build_spec_prepare_prompt, build_spec_prompt
from agent.runner import RateLimitError, run_claude
from agent.spec import count_remaining, count_total, has_remaining, next_item, resolve_md_path


def _seconds_until_reset(reset_str: str) -> float:
    """'4am (Asia/Seoul)' 형식 문자열을 파싱하여 남은 초 반환. 파싱 실패 시 3600."""
    m = re.match(r"(\d{1,2})(?::(\d{2}))?(am|pm)\s*\(([^)]+)\)", reset_str, re.IGNORECASE)
    if not m:
        return 3600.0

    hour, minute, ampm, tz_name = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower(), m.group(4)
    if ampm == "pm" and hour != 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0

    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Asia/Seoul")

    now = datetime.datetime.now(tz)
    reset = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if reset <= now:
        reset += datetime.timedelta(days=1)

    return max((reset - now).total_seconds() + 60, 60.0)  # +60s 여유

if TYPE_CHECKING:
    from bot.reporter import Reporter


class AgentSession:
    """
    채널당 하나의 AgentSession.
    한 번에 하나의 Claude Code 작업만 실행하며,
    실행 중 수신된 피드백은 큐에 쌓아 순차 처리한다.
    """

    def __init__(self) -> None:
        self.is_running: bool = False
        self._stop_requested: bool = False
        self._feedback_queue: deque[str] = deque()
        self._last_md_path: str | None = _load_last_md_path()

    def enqueue_feedback(self, message: str) -> None:
        self._feedback_queue.append(message)

    def request_stop(self) -> None:
        self._stop_requested = True

    async def start(self, command: str, reporter: Reporter) -> None:
        """Discord 명령을 수신하여 처리. MD 경로 감지 시 스펙 모드로 진입."""
        md_path = resolve_md_path(command)
        if md_path:
            self._last_md_path = md_path
            _save_last_md_path(md_path)
            await self._run_spec_loop(md_path, reporter)
        else:
            await reporter.send(f"작업 시작: `{command[:100]}`")
            await self._run(command, reporter)

        await self._process_feedback_queue(reporter)

    async def _run_spec_loop(self, md_path: str, reporter: Reporter) -> None:
        """MD 스펙 파일 기반 반복 개발 루프."""
        total = count_total(md_path)
        remaining = count_remaining(md_path)

        if total == 0:
            await reporter.send(
                f"체크리스트 항목 없음. GDD를 분석하여 구현 체크리스트를 생성합니다.\n"
                f"파일: `{md_path}`"
            )
            await self._run(build_spec_prepare_prompt(md_path), reporter)
            total = count_total(md_path)
            remaining = count_remaining(md_path)

        await reporter.send(
            f"스펙 기반 개발 시작\n"
            f"파일: `{md_path}`\n"
            f"전체 항목: {total}개 / 미완료: {remaining}개"
        )

        self._stop_requested = False
        step = 0
        while has_remaining(md_path):
            if self._stop_requested:
                await reporter.send("중단 요청으로 스펙 루프를 종료합니다.")
                self._stop_requested = False
                return

            # 작업 중 피드백이 쌓인 경우 루프 중단하고 먼저 처리
            if self._feedback_queue:
                await reporter.send("피드백 수신. 현재 스펙 루프를 중단하고 피드백을 먼저 반영합니다.")
                await self._process_feedback_queue(reporter)
                await reporter.send("피드백 반영 완료. 스펙 루프를 재개합니다.")

            step += 1
            remaining = count_remaining(md_path)
            done = total - remaining
            await reporter.send(f"[{done + 1}/{total}] 다음 항목 구현 중...")

            item = next_item(md_path) or ""
            prompt = build_spec_prompt(md_path, item)
            try:
                await self._run(prompt, reporter)
            except RateLimitError as e:
                wait_sec = _seconds_until_reset(e.reset_str)
                resume_time = datetime.datetime.now(ZoneInfo("Asia/Seoul")) + datetime.timedelta(seconds=wait_sec)
                await reporter.send(
                    f"Claude 사용량 한도 도달. {e.reset_str} 리셋 후 자동 재개합니다.\n"
                    f"재개 예정: {resume_time.strftime('%H:%M')} (KST)\n"
                    f"진행 상태: {done}/{total}개 완료, {remaining}개 남음"
                )
                await asyncio.sleep(wait_sec)
                await reporter.send("리셋 완료. 스펙 루프를 재개합니다.")
                continue

        await reporter.send(
            f"전체 스펙 구현 완료.\n"
            f"총 {step}회 실행 / {total}개 항목 처리됨\n"
            f"파일: `{md_path}`"
        )

    def _make_done_handler(self, reporter: Reporter):
        async def on_done(return_code: int) -> None:
            if return_code != 0:
                await reporter.send(f"작업 종료 (exit code: {return_code})")

        return on_done

    async def _process_feedback_queue(self, reporter: Reporter) -> None:
        if self._feedback_queue:
            feedback = self._feedback_queue.popleft()
            await reporter.send(f"피드백 반영 시작: `{feedback[:100]}`")
            await self._run(build_feedback_prompt(feedback), reporter)
            await self._process_feedback_queue(reporter)

    async def _run(self, prompt: str, reporter: Reporter) -> None:
        """빌드된 프롬프트를 실행."""
        self.is_running = True
        reporter.start_streaming()
        try:
            await run_claude(
                prompt,
                on_output=reporter.stream_append,
                on_done=self._make_done_handler(reporter),
                raw_prompt=True,
            )
        finally:
            await reporter.stop_streaming()
            self.is_running = False
