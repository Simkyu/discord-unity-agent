from __future__ import annotations

import asyncio

import discord

_CHUNK_SIZE = 1800  # Discord 2000자 제한에 코드블록 여유분 확보
_FLUSH_INTERVAL = 2.5  # 초 단위 주기적 플러시


class Reporter:
    """
    Discord 채널로 Claude Code 출력을 전달하는 클래스.
    - 단발성 메시지: send()
    - 스트리밍 출력: start_streaming() → stream_append() → stop_streaming()
    """

    def __init__(self, channel: discord.TextChannel) -> None:
        self.channel = channel
        self._buffer: str = ""
        self._flush_task: asyncio.Task | None = None

    async def send(self, text: str) -> None:
        for chunk in _split(text):
            await self.channel.send(chunk)

    def start_streaming(self) -> None:
        self._buffer = ""
        self._flush_task = asyncio.create_task(self._periodic_flush())

    async def stop_streaming(self) -> None:
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._flush()

    async def stream_append(self, text: str) -> None:
        self._buffer += text
        if len(self._buffer) >= _CHUNK_SIZE:
            await self._flush()

    async def _periodic_flush(self) -> None:
        while True:
            await asyncio.sleep(_FLUSH_INTERVAL)
            await self._flush()

    async def _flush(self) -> None:
        if not self._buffer.strip():
            self._buffer = ""
            return

        while len(self._buffer) >= _CHUNK_SIZE:
            chunk = self._buffer[:_CHUNK_SIZE]
            self._buffer = self._buffer[_CHUNK_SIZE:]
            await self.channel.send(f"```\n{chunk}\n```")

        if self._buffer.strip():
            chunk = self._buffer
            self._buffer = ""
            await self.channel.send(f"```\n{chunk}\n```")


def _split(text: str) -> list[str]:
    """긴 텍스트를 Discord 전송 가능한 크기로 분할."""
    result = []
    while len(text) > _CHUNK_SIZE:
        result.append(text[:_CHUNK_SIZE])
        text = text[_CHUNK_SIZE:]
    if text:
        result.append(text)
    return result
