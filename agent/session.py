from __future__ import annotations

import asyncio
from collections import deque
from typing import TYPE_CHECKING

from agent.prompt import build_feedback_prompt
from agent.runner import run_claude

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
        await reporter.send(f"작업 시작: `{command[:100]}`")
        await self._run(command, reporter)
        await self._process_feedback_queue(reporter)

    def _make_done_handler(self, reporter: Reporter):
        async def on_done(return_code: int) -> None:
            if return_code == 0:
                await reporter.send("작업 완료.")
            else:
                await reporter.send(f"작업 종료 (exit code: {return_code})")

        return on_done

    async def _process_feedback_queue(self, reporter: Reporter) -> None:
        if self._feedback_queue:
            feedback = self._feedback_queue.popleft()
            await reporter.send(f"피드백 반영 시작: `{feedback[:100]}`")
            await self._run(build_feedback_prompt(feedback), reporter)
            await self._process_feedback_queue(reporter)

    async def _run(self, prompt: str, reporter: Reporter) -> None:
        """빌드된 프롬프트를 직접 실행. start()는 사용자 명령용, _run()은 내부 재귀용."""
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
