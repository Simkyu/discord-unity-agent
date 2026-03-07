from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from bot.handlers import MessageHandler

if TYPE_CHECKING:
    from agent.session import AgentSession


def create_client(session: AgentSession) -> discord.Client:
    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)
    handler = MessageHandler(session)

    @client.event
    async def on_ready() -> None:
        print(f"[Bot] 준비 완료: {client.user}")

    @client.event
    async def on_message(message: discord.Message) -> None:
        await handler.handle(message)

    return client
