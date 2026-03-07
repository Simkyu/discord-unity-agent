import asyncio
from collections.abc import Awaitable, Callable

import config
from agent.prompt import build_prompt

OnOutputCallback = Callable[[str], Awaitable[None]]
OnDoneCallback = Callable[[int], Awaitable[None]]


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
    async for line in proc.stdout:
        decoded = line.decode("utf-8", errors="replace")
        await on_output(decoded)

    await proc.wait()
    await on_done(proc.returncode)
