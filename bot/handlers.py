from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord

import config
from bot.reporter import Reporter

if TYPE_CHECKING:
    from agent.session import AgentSession


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
