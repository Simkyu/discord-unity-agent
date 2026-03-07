from __future__ import annotations

import asyncio
from collections import deque
from typing import TYPE_CHECKING

from agent.prompt import build_feedback_prompt, build_spec_prompt
from agent.runner import run_claude
from agent.spec import count_remaining, count_total, has_remaining, resolve_md_path

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
        self._feedback_queue: deque[str] = deque()

    def enqueue_feedback(self, message: str) -> None:
        self._feedback_queue.append(message)

    async def start(self, command: str, reporter: Reporter) -> None:
        """Discord 명령을 수신하여 처리. MD 경로 감지 시 스펙 모드로 진입."""
        md_path = resolve_md_path(command)
        if md_path:
            await self._run_spec_loop(md_path, reporter)
        else:
            await reporter.send(f"작업 시작: `{command[:100]}`")
            await self._run(command, reporter)

        await self._process_feedback_queue(reporter)

    async def _run_spec_loop(self, md_path: str, reporter: Reporter) -> None:
        """MD 스펙 파일 기반 반복 개발 루프."""
        total = count_total(md_path)
        remaining = count_remaining(md_path)

        await reporter.send(
            f"스펙 기반 개발 시작\n"
            f"파일: `{md_path}`\n"
            f"전체 항목: {total}개 / 미완료: {remaining}개"
        )

        step = 0
        while has_remaining(md_path):
            # 작업 중 피드백이 쌓인 경우 루프 중단하고 먼저 처리
            if self._feedback_queue:
                await reporter.send("피드백 수신. 현재 스펙 루프를 중단하고 피드백을 먼저 반영합니다.")
                await self._process_feedback_queue(reporter)
                await reporter.send("피드백 반영 완료. 스펙 루프를 재개합니다.")

            step += 1
            remaining = count_remaining(md_path)
            done = total - remaining
            await reporter.send(f"[{done + 1}/{total}] 다음 항목 구현 중...")

            prompt = build_spec_prompt(md_path)
            await self._run(prompt, reporter)

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
