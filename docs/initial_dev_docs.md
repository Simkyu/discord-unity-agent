프로젝트 개요: Discord 기반 Unity 자율 개발 시스템

1. 핵심 목표

Interface: Discord를 리모컨으로 사용하여 명령 하달 및 결과 보고 수신.

Engine: Claude Code CLI를 사용하여 자율적인 코드 수정, 컴파일 에러 해결 및 반복 개발 수행.

Execution: Unity MCP 및 FileSystem 도구를 활용해 실제 프로젝트 자산 및 스크립트 제어.

Automation: 사용자의 승인 없이도(--dangerously-skip-permissions) 목표 달성 시까지 자율 루프 가동.

2. 시스템 아키텍처

[Discord User] ↔ [Discord Bot (Python Middle-ware)] ↔ [Claude Code CLI] ↔ [Unity MCP / Local Files]

3. 구성 요소 및 설정값 (전달 필요)

Discord Bot: discord.py 기반의 중계기.

특정 Guild ID(ALLOWED_GUILD_ID) 및 특정 채널 내에서만 작동.

사용자 메시지를 claude -p 명령어로 래핑하여 실행.

Claude Code:

Unity 프로젝트 루트 디렉토리에서 실행.

--dangerously-skip-permissions 플래그를 기본으로 사용하여 완전 자동화.

MCP Servers (이미 설정됨):

discord-mcp: 메시지 전송 및 채널 관리용.

unity-mcp: 유니티 씬 분석 및 오브젝트 제어용.

filesystem: 코드 수정 및 문서(*.md) 업데이트용.

4. Claude에게 내리는 특수 지침 (System Prompt)

너는 이제부터 이 프로젝트의 자율 개발 요원이다. 다음 프로세스를 준수하라:

명령 수신: 중계 봇을 통해 전달된 Discord 메시지를 최종 목표로 인식한다.

자율 루프: 목표를 달성할 때까지 [분석 -> 수정 -> 컴파일 확인 -> 재수정] 과정을 스스로 반복한다.

보고: 모든 작업 단계와 최종 결과는 Discord 전용 MCP를 사용하거나 중계 봇의 출력값을 통해 Discord 채널에 실시간으로 보고한다.

문서화: 개발 완료 시마다 프로젝트 내 Docs/ 폴더의 개발 일지를 마크다운 형식으로 자동 갱신한다.

5. 실행 환경 (Local)

OS: macOS

Unity Path: [사용자 입력 필요]

Claude Code Path: /usr/local/bin/claude (또는 which claude 결과값)

6. 초기 가동 시나리오

파이썬 중계 봇(bot.py) 실행.

디스코드에서 "현재 유니티 프로젝트 상태 보고하고, 캐릭터 컨트롤러 스크립트의 이동 로직 최적화해줘" 명령 투척.

Claude Code가 자율적으로 작업을 수행하고 디스코드로 완료 보고 및 수정 내역 전송.
