from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord
from discord import app_commands

import config
from bot.handlers import MessageHandler
from bot.reporter import Reporter

if TYPE_CHECKING:
    from agent.session import AgentSession


def create_client(session: AgentSession) -> discord.Client:
    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    handler = MessageHandler(session)

    @client.event
    async def on_ready() -> None:
        await tree.sync(guild=discord.Object(id=config.ALLOWED_GUILD_ID))
        print(f"[Bot] 준비 완료: {client.user}")

    @client.event
    async def on_message(message: discord.Message) -> None:
        await handler.handle(message)

    guild = discord.Object(id=config.ALLOWED_GUILD_ID)

    @tree.command(guild=guild, name="이어서", description="중단된 스펙 루프를 이어서 진행합니다.")
    async def cmd_resume(interaction: discord.Interaction) -> None:
        if interaction.channel_id != config.ALLOWED_CHANNEL_ID:
            await interaction.response.send_message("허용된 채널이 아닙니다.", ephemeral=True)
            return
        reporter = Reporter(interaction.channel)  # type: ignore[arg-type]
        if session._last_md_path:
            await interaction.response.send_message("스펙 루프를 재개합니다.")
            asyncio.create_task(session._run_spec_loop(session._last_md_path, reporter))
        else:
            await interaction.response.send_message("이어서 진행할 스펙 파일이 없습니다. MD 파일 경로를 포함해서 명령해주세요.")

    @tree.command(guild=guild, name="상태", description="현재 스펙 진행 상태를 확인합니다.")
    async def cmd_status(interaction: discord.Interaction) -> None:
        if interaction.channel_id != config.ALLOWED_CHANNEL_ID:
            await interaction.response.send_message("허용된 채널이 아닙니다.", ephemeral=True)
            return
        from agent.spec import count_remaining, count_total
        md_path = session._last_md_path
        if not md_path:
            await interaction.response.send_message("등록된 스펙 파일이 없습니다.")
            return
        total = count_total(md_path)
        remaining = count_remaining(md_path)
        done = total - remaining
        status = "실행 중" if session.is_running else "대기 중"
        await interaction.response.send_message(
            f"**스펙 진행 상태** ({status})\n"
            f"파일: `{md_path}`\n"
            f"완료: {done}/{total}개 | 남음: {remaining}개"
        )

    @tree.command(guild=guild, name="중단", description="현재 실행 중인 작업을 중단합니다.")
    async def cmd_stop(interaction: discord.Interaction) -> None:
        if interaction.channel_id != config.ALLOWED_CHANNEL_ID:
            await interaction.response.send_message("허용된 채널이 아닙니다.", ephemeral=True)
            return
        if not session.is_running:
            await interaction.response.send_message("현재 실행 중인 작업이 없습니다.")
            return
        session.request_stop()
        await interaction.response.send_message("중단 요청을 전송했습니다. 현재 항목 완료 후 종료됩니다.")

    return client
