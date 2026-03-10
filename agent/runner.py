import asyncio
import re
from collections.abc import Awaitable, Callable

import config
from agent.prompt import build_prompt

OnOutputCallback = Callable[[str], Awaitable[None]]
OnDoneCallback = Callable[[int], Awaitable[None]]

_RATE_LIMIT_RE = re.compile(
    r"resets\s+(\d{1,2}(?::\d{2})?(?:am|pm))\s*\(([^)]+)\)",
    re.IGNORECASE,
)


class RateLimitError(Exception):
    """Claude CLI rate limit 도달 시 발생."""

    def __init__(self, reset_str: str) -> None:
        self.reset_str = reset_str
        super().__init__(f"Rate limit hit, resets: {reset_str}")


async def run_claude(
    command: str,
    on_output: OnOutputCallback,
    on_done: OnDoneCallback,
    raw_prompt: bool = False,
) -> None:
    """
    Claude Code CLI를 서브프로세스로 실행한다.
    raw_prompt=True 이면 command를 그대로 프롬프트로 사용 (이미 빌드된 경우).
    stdout은 on_output으로 라인 단위 스트리밍, 종료 시 on_done 호출.
    """
    prompt = command if raw_prompt else build_prompt(command)

    proc = await asyncio.create_subprocess_exec(
        config.CLAUDE_PATH,
        "--dangerously-skip-permissions",
        "-p",
        prompt,
        cwd=config.UNITY_PROJECT_PATH,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    assert proc.stdout is not None
    rate_limit_str: str | None = None
    async for line in proc.stdout:
        decoded = line.decode("utf-8", errors="replace")
        await on_output(decoded)
        m = _RATE_LIMIT_RE.search(decoded)
        if m:
            rate_limit_str = f"{m.group(1)} ({m.group(2)})"

    await proc.wait()
    if rate_limit_str:
        raise RateLimitError(rate_limit_str)
    await on_done(proc.returncode)
