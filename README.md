# discord-unity-agent

Discord 채널을 인터페이스로 사용하여 Claude Code에 개발 명령을 내리고, 자율 개발 루프의 진행 상황을 실시간으로 보고받는 시스템.

실제 코드 작성, 디버깅, Unity 씬 제어는 Claude Code가 연결된 MCP(unity-mcp, filesystem 등)를 통해 수행한다.

---

## 기능

- **Discord 명령 수신**: 지정된 Guild + Channel에서만 명령을 수신하여 Claude Code로 전달
- **자율 개발 루프**: Claude Code가 문서 참조 → 코드 수정 → 검증 → 재수정을 목표 달성까지 반복
- **실시간 보고**: Claude Code의 stdout을 Discord 채널로 스트리밍 (2.5초 주기 플러시)
- **피드백 반영**: 작업 진행 중 새 메시지가 오면 큐에 적재 후 현재 작업 완료 즉시 반영
- **개발일지 자동 갱신**: 작업 완료 시 `docs/dev_log.md` 자동 업데이트 (Claude Code가 수행)
- **자동 커밋**: 기능/수정 단위 완료 시 `[TYPE] 한 줄 설명` 형식으로 git commit (PR 없음)

---

## 아키텍처

```
[Discord 사용자]
      |  명령 전송 (지정 채널)
      v
[bot/ - Discord Bot]
  handlers.py  ← guild/channel 필터링, 세션 디스패치
  reporter.py  ← stdout 버퍼링 및 Discord 전송
      |
      v
[agent/ - Claude Code 실행 레이어]
  session.py   ← 작업 큐 관리 (실행 중 피드백 처리)
  runner.py    ← claude CLI 서브프로세스 실행 및 스트리밍
  prompt.py    ← 시스템 컨텍스트 + 사용자 명령 조합
      |
      v
[Claude Code CLI (--dangerously-skip-permissions)]
      |  자율 루프: 분석 → 수정 → 검증 → 재수정
      v
[Unity MCP / FileSystem MCP]  ← Claude Code의 MCP 설정에서 관리
      |
      v
[Discord 사용자]  ← 진행 보고 + 완료 요약
```

---

## 프로젝트 구조

```
discord-unity-agent/
├── main.py                  # 진입점
├── config.py                # 환경변수 로드
├── requirements.txt
├── .env.example
├── bot/
│   ├── client.py            # Discord 클라이언트, 이벤트 등록
│   ├── handlers.py          # 메시지 필터 및 세션 디스패치
│   └── reporter.py          # Discord 전송 (버퍼링, 청크 분할)
├── agent/
│   ├── prompt.py            # 프롬프트 빌더 (시스템 컨텍스트 + 명령)
│   ├── runner.py            # claude CLI 서브프로세스 실행
│   └── session.py           # 작업 상태 및 피드백 큐 관리
├── git/
│   └── committer.py         # 봇 레벨 수동 커밋 유틸리티
└── docs/
    ├── initial_dev_docs.md  # 시스템 설계 문서
    └── dev_log.md           # 에이전트 자동 갱신 개발일지
```

---

## 시작하기

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 아래 항목을 채운다:

| 변수 | 설명 |
|------|------|
| `DISCORD_TOKEN` | Discord Bot 토큰 |
| `ALLOWED_GUILD_ID` | 명령을 허용할 Discord 서버 ID |
| `ALLOWED_CHANNEL_ID` | 명령을 허용할 채널 ID |
| `UNITY_PROJECT_PATH` | Unity 프로젝트 루트 경로 (절대경로) |
| `CLAUDE_PATH` | claude CLI 경로 (기본값: `claude`) |

> **Unity MCP 설정은 여기서 하지 않는다.**
> Unity MCP는 Claude Code의 MCP 설정(`~/.claude/` 등)에 등록되어 있으면 자동으로 사용된다.

### 3. 실행

```bash
python main.py
```

### 4. Discord에서 명령

지정한 채널에서 자연어로 입력하면 바로 실행된다. 별도 prefix나 명령어 불필요.

| 상황 | 방법 |
|------|------|
| 일반 개발 명령 | 채널에 자연어 입력: `PlayerController 이동 로직 최적화해줘` |
| MD 스펙 기반 개발 (경로) | 텍스트로 경로 포함: `docs/feature_spec.md 기반으로 개발 시작해줘` |
| MD 스펙 기반 개발 (업로드) | MD 파일을 채널에 첨부. 캡션으로 추가 지시사항 입력 가능 |
| 작업 중 피드백 | 채널에 메시지 입력 (큐에 적재 → 현재 작업 완료 후 자동 반영) |

#### MD 파일 기반 반복 개발 워크플로우

메시지에 `.md` 파일 경로가 포함되면 자동으로 스펙 모드로 진입한다.

```
Discord: docs/feature_spec.md 기반으로 개발해줘
  → 봇이 체크리스트 항목 수 파악 → Discord 보고
  → LOOP (미완료 항목이 없을 때까지):
      Claude 실행 (미완료 항목 1개만 구현)
        [진행] 항목명 보고
        → 구현 → - [x] 체크 → git commit → [완료] 보고
      봇이 MD 재확인 → 미완료 항목 있으면 재실행
  → 전체 완료 → Discord 보고
```

**스펙 MD 파일 형식 (체크리스트):**
```markdown
## 구현 목록
- [ ] 캐릭터 이동 시스템 구현
- [ ] 점프 로직 추가
- [ ] 카메라 추적 스크립트 작성
- [ ] 충돌 처리 최적화
```

- 항목은 위에서부터 순서대로 처리된다
- 완료된 항목은 `- [x]`로 자동 변경된다
- 스펙 진행 중 피드백이 오면 현재 항목 완료 후 피드백을 먼저 반영하고 스펙을 재개한다

---

## Discord 출력 형식

Claude Code는 아래 태그를 붙여 보고한다:

| 태그 | 의미 |
|------|------|
| `[시작]` | 작업 착수, 목표 요약 |
| `[진행]` | 각 단계 완료 시 |
| `[에러-N]` | N번째 에러 발생 + 수정 방향 |
| `[재시도]` | 수정 후 재검증 |
| `[완료]` | 성공, 변경 파일 목록 + git commit 수행 |
| `[실패]` | 10회 루프 초과 시 사유 보고 |

---

## Git 전략

- 기능(feature) 또는 수정(fix) 단위 완료 시마다 자동 커밋
- 커밋 메시지 형식: `[TYPE] 한 줄 설명`
  - `[ADD]`, `[FIX]`, `[REFACTOR]`, `[REMOVE]`, `[DOCS]`
- PR 생성 없음
