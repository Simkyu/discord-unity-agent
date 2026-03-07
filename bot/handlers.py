from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import discord

import config
from bot.reporter import Reporter

if TYPE_CHECKING:
    from agent.session import AgentSession

_DOCS_DIR = Path(config.UNITY_PROJECT_PATH) / "docs"


class MessageHandler:
    def __init__(self, session: AgentSession) -> None:
        self._session = session

    async def handle(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if not message.guild or message.guild.id != config.ALLOWED_GUILD_ID:
            return
        if message.channel.id != config.ALLOWED_CHANNEL_ID:
            return

        reporter = Reporter(message.channel)  # type: ignore[arg-type]

        # MD 파일 첨부 감지
        md_attachment = _find_md_attachment(message)
        if md_attachment:
            await self._handle_attachment(md_attachment, message.content.strip(), reporter)
            return

        content = message.content.strip()
        if not content:
            return

        if self._session.is_running:
            self._session.enqueue_feedback(content)
            await reporter.send(
                f"피드백 수신 (`{content[:80]}`). 현재 작업 완료 후 반영합니다."
            )
        else:
            asyncio.create_task(self._session.start(content, reporter))

    async def _handle_attachment(
        self,
        attachment: discord.Attachment,
        caption: str,
        reporter: Reporter,
    ) -> None:
        """MD 첨부파일을 docs/ 에 저장하고 스펙 루프 시작."""
        _DOCS_DIR.mkdir(parents=True, exist_ok=True)
        save_path = _DOCS_DIR / attachment.filename

        await reporter.send(
            f"MD 파일 수신: `{attachment.filename}`\n"
            f"`{save_path}` 에 저장 후 스펙 개발을 시작합니다."
        )

        content = await attachment.read()
        save_path.write_bytes(content)

        # 캡션이 있으면 추가 지시사항으로 전달, 없으면 스펙 루프만 실행
        command = f"{save_path} 기반으로 개발해줘"
        if caption:
            command = f"{save_path} 기반으로 개발해줘. 추가 지시: {caption}"

        if self._session.is_running:
            self._session.enqueue_feedback(command)
            await reporter.send("현재 작업 완료 후 업로드된 스펙을 처리합니다.")
        else:
            asyncio.create_task(self._session.start(command, reporter))


def _find_md_attachment(message: discord.Message) -> discord.Attachment | None:
    """메시지 첨부파일 중 첫 번째 .md 파일 반환."""
    for attachment in message.attachments:
        if attachment.filename.endswith(".md"):
            return attachment
    return None
