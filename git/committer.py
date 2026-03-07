"""
Claude Code가 직접 bash 도구로 git commit을 수행하는 것이 기본 흐름이지만,
이 모듈은 봇 레벨에서 수동으로 커밋이 필요한 경우를 위한 유틸리티다.
"""
import asyncio

import config


async def commit(message: str) -> int:
    """
    Unity 프로젝트 경로에서 git add -A 후 커밋.
    message 형식: "[TYPE] 한 줄 설명"
    반환값: git commit exit code
    """
    add = await asyncio.create_subprocess_exec(
        "git", "add", "-A",
        cwd=config.UNITY_PROJECT_PATH,
    )
    await add.wait()

    commit_proc = await asyncio.create_subprocess_exec(
        "git", "commit", "-m", message,
        cwd=config.UNITY_PROJECT_PATH,
    )
    await commit_proc.wait()
    return commit_proc.returncode
