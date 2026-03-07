# Discord Unity Agent - 프로젝트 개요 및 개발 지침

## 1. 핵심 목표

- **Interface**: Discord 특정 채널(Guild ID 기반)을 명령 인터페이스로 사용. 명령 수신 및 결과 보고.
- **Engine**: Claude Code CLI를 서브프로세스로 실행하여 자율적인 코드 작성, 에러 해결, 반복 개발 수행.
- **Execution**: Unity MCP 및 FileSystem 도구를 활용해 실제 Unity 프로젝트 자산 및 스크립트 제어.
- **Automation**: `--dangerously-skip-permissions` 플래그로 사용자 승인 없이 자율 루프 가동.

---

## 2. 시스템 아키텍처

```
[Discord User]
     |  명령 전송 (특정 채널)
     v
[bot.py - Discord Bot (discord.py)]
     |  guild_id / channel_id 필터링
     |  명령을 Claude Code CLI 서브프로세스로 래핑하여 실행
     v
[Claude Code CLI (--dangerously-skip-permissions)]
     |  자율 개발 루프 (분석 → 코드 수정 → 빌드/컴파일 확인 → 재수정)
     |  docs/ 문서 참조하여 컨텍스트 유지 및 디버깅
     v
[Unity MCP / FileSystem MCP]
     |  실제 Unity 프로젝트 파일 조작
     v
[bot.py]
     |  Claude Code 출력을 Discord 채널로 전송 (진행 보고 + 최종 결과)
     v
[Discord User]
```

---

## 3. 구성 요소

### Discord Bot (`bot.py`)
- `discord.py` 기반 중계 봇
- `ALLOWED_GUILD_ID` 및 특정 `CHANNEL_ID`에서만 명령 수신
- 수신한 메시지를 Claude Code CLI 서브프로세스로 전달
- Claude Code의 stdout/stderr를 Discord 채널로 실시간 스트리밍 보고
- **개발 중 피드백 수신**: 작업이 진행 중일 때 새 메시지가 오면 이를 피드백으로 인식하여 진행 중인 Claude Code 세션에 주입하거나, 현재 작업 완료 후 즉시 반영

### Claude Code CLI
- Unity 프로젝트 루트 디렉토리에서 실행
- `--dangerously-skip-permissions` 플래그 필수 (완전 자동화)
- 실행 방식: `claude -p "<명령>" --dangerously-skip-permissions` (단발성) 또는 장기 세션으로 운영

### MCP Servers (사전 설정됨)
- `unity-mcp`: Unity 씬 분석 및 오브젝트 제어
- `filesystem`: 코드 수정 및 문서(`docs/*.md`) 읽기/쓰기
- `discord-mcp`: Discord 채널 메시지 전송 (보조 보고 수단)

---

## 4. Claude Code 자율 개발 루프 (핵심 동작 원칙)

Claude Code가 명령을 수신하면 다음 루프를 목표 달성까지 반복한다:

```
1. [문서 참조]
   - docs/ 폴더의 관련 문서(개발일지, 설계 문서 등)를 먼저 읽어 현재 상태와 맥락 파악

2. [분석]
   - 목표 달성에 필요한 파일/씬/스크립트 분석

3. [코드 수정]
   - Unity 스크립트 또는 관련 파일 수정

4. [검증]
   - 컴파일 에러 또는 로직 오류 확인 (Unity MCP 활용)
   - 에러 발생 시 → 3번으로 돌아가 재수정 (자율 반복)

5. [보고]
   - 각 단계 진행 상황을 Discord 채널에 실시간 보고
   - 최종 완료 시 작업 요약 및 변경 내역 보고

6. [문서화]
   - 작업 완료 시 docs/dev_log.md (개발일지)를 마크다운으로 자동 갱신
   - 갱신 항목: 날짜, 작업 내용, 변경 파일, 특이사항
```

---

## 5. 개발 중 피드백 반영

- 작업 진행 중 Discord에서 새 메시지(피드백/수정 요청)가 오면 **최우선으로 반영**
- 피드백은 현재 루프에 즉시 주입하거나, 현재 단계 완료 후 다음 루프에 반영
- 피드백 수신 시 Discord에 "피드백 수신, 반영합니다" 응답 후 작업 조정

---

## 6. Git 전략

- **Commit**: 기능 단위(feature), 수정 단위(fix) 완료 시마다 한 줄 커밋 메시지로 자동 커밋
  - 예: `[ADD] 캐릭터 이동 로직 최적화`, `[FIX] 컴파일 에러 수정 - PlayerController`
- **PR**: 보류 (미운영)
- **Branch**: 현재 `dev` 브랜치에서 작업

---

## 7. 실행 환경

- **OS**: macOS
- **Unity 프로젝트 경로**: 별도 지정 필요 (bot.py의 `UNITY_PROJECT_PATH` 환경변수)
- **Claude Code 경로**: `which claude` 결과값 사용
- **Python**: discord.py 의존성 설치 필요 (`pip install discord.py`)

---

## 8. 초기 가동 시나리오

1. `bot.py` 실행 (Discord Bot 기동)
2. 허용된 Discord 채널에서 명령 입력:
   ```
   현재 Unity 프로젝트 상태 보고하고, PlayerController 이동 로직 최적화해줘
   ```
3. Claude Code가 자율 루프로 작업 수행
4. 각 단계별 진행 상황이 Discord 채널에 실시간 보고
5. 완료 시 변경 내역 요약 보고 + 개발일지(`docs/dev_log.md`) 자동 갱신 + git commit

---

## 9. 개발일지 형식 (`docs/dev_log.md`)

```markdown
## [YYYY-MM-DD] 작업 제목

- **명령 출처**: Discord 채널
- **작업 내용**: ...
- **변경 파일**: ...
- **결과**: 성공 / 실패 (실패 시 사유)
- **특이사항**: ...
```
