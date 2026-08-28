# Agent Checkpoint

[English](README.md) | **한국어**

Agent Checkpoint는 새 AI 에이전트 세션이 실제로 필요로 하는 최소한의 프로젝트
상태를 보존하기 위한 이식 가능한 스킬이자 커맨드라인 도구입니다. 검증된
진행 상황은 작업 단위 `PROGRESS.md`에 남기고, 상세한 계획 자료는 템플릿
기반 work package에 넣으며, 다음 세션에게는 압축된 대화를 재구성하라고
요구하는 대신 저장소 루트의 `CONTINUE_PROMPT.md`부터 시작하는 결정론적
읽기 순서를 제공합니다.

이 도구는 채팅 기록, 메모리 데이터베이스, Git diff 저장소가 **아닙니다** —
의도적으로 그렇게 설계했습니다. 각 체크포인트는 현재 목표, 검증된 진행
상황, 현재 초점, 다음 행동, 지속적인 결정 사항만 기록합니다. 상세 계획,
증거, 게이트는 `.agent-checkpoint/work/<id>/` 아래에 남습니다.

## 이 스킬이 제공하는 것

- 안전한 체크포인트 작성, 검증, 회전/보관, 범위가 제한된 resume/handoff
  컨텍스트, 진단 기능을 갖춘 의존성 없는 Python 3.11+ CLI.
- 열 가지 개발 워크플로 템플릿: `project`, `feature`, `bugfix`, `refactor`,
  `upgrade`, `migration`, `performance`, `integration`, `release`, `spike`.
- 호환되는 에이전트가 범위·성공 기준·제약 조건을 임의로 지어내는 대신
  누락된 계획 입력값을 사용자에게 묻도록 지시하는 범용 `SKILL.md`.
- Claude Code, Codex, OpenCode, Gemini CLI용 네이티브 어댑터 — 각 어댑터는
  해당 호스트가 실제로 지원하는 라이프사이클 동작만 노출합니다.
- 안전 경계: 원자적 쓰기, 잠금, 프로젝트 경로 제한, 자격 증명·diff 콘텐츠
  거부, 그리고 Git 파일 내용을 읽거나 저장하지 않는 Git 인지 진단 힌트.

## 작업 항목이 흐르는 방식

1. 작업 항목을 시작할 때 워크플로 타입을 선택하고 work package를
   구체화합니다. 이 명령은 템플릿의 큰 사본이 아니라 간결한 포인터
   체크포인트를 기록합니다.

   ```bash
   agent-checkpoint workflow --type feature --id current
   ```

2. 계획을 세우기 전, 스킬은 선택한 템플릿에 필요한 정보 중 빠진 것 —
   목표, 범위, 성공 기준, 제약 조건, 영향 범위 — 을 사용자에게 묻습니다.
   확인된 사실만 기록합니다.

3. 작업 중에는 다섯 개의 필수 헤딩을 사용해 간결한 체크포인트를 작성하고,
   구체적인 검증 결과는 별도로 첨부합니다. diff, 자격 증명, 추측성 요약을
   붙여넣지 마세요.

4. handoff나 컴팩션 이후 새 세션을 시작하면 저장소 루트의
   `CONTINUE_PROMPT.md`를 읽습니다. 이 파일이 활성 work package를
   지목하므로, 그 패키지의 `CURRENT.md`를 따라간 뒤 자체
   `CONTINUE_PROMPT.md`를 읽고, 문서화된 Current Target만 실행합니다.

이 설계 덕분에 각 work package의 `PROGRESS.md`는 짧은 라우팅 문서로
유지되고, 상세한 실행 상태의 원천은 템플릿 패키지에 남습니다.

## 열세 개의 스킬

`checkpoint`와 `checkpoint-save`는 이름 접두사는 같지만 하는 일이 달라
혼동하기 쉽습니다 — `checkpoint`는 순수 라우터입니다: `work status`를
실행하고 `next_skill`을 읽어 정확히 그 스킬 하나만 호출하며, 요약은
직접 작성하지 않습니다. `checkpoint-save`는 세션 요약을 담당하는
짝입니다: 이번 세션에 일어난 일을 기록하고, work package가 아직 없으면
이미 끝난 작업을 근거로 새 작업을 계획하는 대신 그 작업 자체를 위한
work package를 소급 생성합니다. 나머지 열한 개는 각각 work package
생애주기의 한 단계를 담당하며, 에이전트의 판단이 아니라 유닛의 현재
상태로 선택됩니다. 전체 순서가 정해진 라우팅 표는
`skills/_checkpoint-shared/chain-v1.md`를 참고하세요.

| 스킬 | 발동 조건 | 하는 일 |
|---|---|---|
| `checkpoint` | 항상, 가장 먼저 | `work status --json`을 읽어 `next_skill`에 지정된 스킬로 위임 |
| `checkpoint-save` | 무슨 일이 있었는지 기록하고 싶을 때 언제든 — 세션 도중, 또는 compaction/새 세션 전 | work package가 있으면 `write`로 delta 요약 작성; 없으면 워크플로 타입을 추천하고(사용자 확인 후) 패키지를 생성해 세션의 실제 작업을 근거로 brief를 소급 채우며 — 계획이 이미 끝난 것으로 보이고 사용자가 확인한 경우에만 `checkpoint-plan`으로 넘김 |
| `checkpoint-select-workflow` | 아직 상태 블록이 전혀 없음 | 열 가지 워크플로 타입 중 무엇이 맞는지 묻고 `agent-checkpoint workflow --type TYPE --id current`로 패키지 생성 |
| `checkpoint-brainstorm` | 패키지는 있지만 `brief_confirmed`가 false | 목표·범위·성공 기준·제약 조건·영향 범위를 물어보고, 확인된 답변만 기록 |
| `checkpoint-plan` | brief는 확정됐지만 유닛 목록이 비어 있거나 현재 유닛이 superseded | 유닛 ID에 연결된 번호 매긴 단계로 `PLAN.md` 작성 — 계획을 수정하는 유일한 스킬 |
| `checkpoint-claim` | 현재 유닛이 `pending` 또는 `ready` | 유닛의 의존성이 충족됐는지 확인한 뒤 `work start`로 `running`으로 전환 |
| `checkpoint-execute` | 현재 유닛이 `running`이고 종류가 `step` | 단계를 구현 — 범위 내 소소한 발견은 자체 증거에 포함하고, 큰 발견은 handoff 리포트로 유예 |
| `checkpoint-verify-gate` | 현재 유닛이 `running`이고 종류가 `gate` | 교차 영역 인수 기준을 확인 — 하나라도 미충족이면 부분 통과가 아니라 실패 |
| `checkpoint-evidence` | 실행 또는 게이트 검증이 방금 끝남 | 매니페스트가 요구하는 섹션에 맞춰 증거 문서를 검증한 뒤 `work pass` 또는 `work fail` 실행 |
| `checkpoint-diagnose` | 현재 유닛이 `failed`이고 `root_cause_fingerprint` 없음 | 실패를 분석해 fingerprint를 기록 — 복구 방법은 직접 선택하지 않음 |
| `checkpoint-recover` | 현재 유닛이 `failed`(fingerprint 있음) 또는 `blocked` | `allowed_events` 중 `retry`, `replan`, `supersede`, `block`, `unblock` 하나를 골라 적용 |
| `checkpoint-handoff` | 모든 유닛이 `passed` | 최종 handoff 컨텍스트를 렌더링 — 열린 handoff 리포트마다 먼저 트리와 대조해 해결됐는지 확인한 뒤 처리 방법을 묻음 |
| `checkpoint-inspect` | 읽기 전용 상태 조회가 필요할 때 언제든 | 아무것도 쓰지 않고 상태만 보고 — 전이/복구 명령을 호출하지 않음 |

## 어댑터별 동작 한눈에 보기

| 대상 | 체크포인트 동작 | 새 세션 동작 |
|---|---|---|
| Claude Code | 체크포인트가 전혀 없을 때만 자동 PreCompact 부트스트랩; 수동 명령도 계속 사용 가능 | 훅이 새로 시작된 세션에게 루트 `CONTINUE_PROMPT.md`를 읽고 work package 포인터를 따라가라고 알림 |
| Codex | 수동 스킬 및 CLI 워크플로 | 체크포인트/work package를 수동으로 읽음 |
| OpenCode | 수동 스킬, 커맨드, CLI 워크플로 | 체크포인트/work package를 수동으로 읽음 |
| Gemini CLI | 체크포인트 상태가 없거나 오래됐을 때 사전 압축 권고 메시지 | 체크포인트/work package를 수동으로 읽음 |

자동 동작은 절대 작업 요약을 지어내지 않습니다. 특히 Claude 부트스트랩
체크포인트는 라이프사이클 훅이 이전 대화를 들여다볼 수 없기 때문에
자신을 명확히 placeholder로 표시합니다. 활성 작업이 파악되는 대로
작업 특화된 수동 체크포인트로 교체하세요.

Claude Code가 기존 체크포인트 없이 컴팩션에 도달하면, 훅이 유효한
부트스트랩 항목 하나를 작성하고 현재 처리 경로를 멈춘 뒤 사용자에게 새
Claude Code 세션을 시작하라고 요청합니다. 그 새로운 `startup` 세션은
이전 이력을 재구성하는 본문이 아니라, 루트 `CONTINUE_PROMPT.md` ->
`CURRENT.md` -> 자체 `CONTINUE_PROMPT.md`라는 읽기 순서만 받습니다.
부트스트랩 쓰기가 실패하면 체크포인트 없이 진행하는 대신 컴팩션 자체가
차단됩니다. 기존 체크포인트는 그대로 유지됩니다.

## 요구 사항

- `PATH`에 Python 3.11 이상
- 브랜치/worktree/ignore/추적 파일 진단을 위한 Git

## CLI 설치

CLI는 의존성 없는 Python 3.11+ 프로그램입니다. 체크아웃한 저장소에서
`bin/`을 `PATH`에 추가하거나, 런처를 기존 `PATH` 디렉터리에
심링크하세요:

```bash
ln -s /absolute/path/to/agent-checkpoint/bin/agent-checkpoint /usr/local/bin/agent-checkpoint
agent-checkpoint --help

# 또는 설치 없이 직접 실행
/absolute/path/to/agent-checkpoint/bin/agent-checkpoint --help
```

`PATH`의 `python3`가 3.11+로 연결되지 않는다면 `AGENT_CHECKPOINT_PYTHON`을
설정해 특정 Python 실행 파일을 지정하세요.

## 스킬 설치

### Claude Code 플러그인 (Claude Code에서 권장)

호스트 번들은 체크인되어 있지 않고 필요할 때 빌드합니다. 먼저 Claude
Code 번들을 빌드하세요 — 이 번들 자체가 Claude Code 플러그인
마켓플레이스(`.claude-plugin/marketplace.json`)이므로, Claude Code가
스킬·커맨드·훅을 한 단계로 함께 설치할 수 있습니다. 마켓플레이스 추가는
저장소 루트가 아니라 빌드된 번들을 가리켜야 합니다:

```bash
# 로컬 체크아웃에서 번들 빌드
python3 tools/build_adapter.py claude-code --output /absolute/path/to/bundle

# 이후, 셸에서
claude plugin marketplace add /absolute/path/to/bundle
claude plugin install agent-checkpoint@agent-checkpoint

# 또는 Claude Code 세션 내부에서
/plugin marketplace add /absolute/path/to/bundle
/plugin install agent-checkpoint@agent-checkpoint
```

이 경로만이 순수 `SKILL.md` 파일뿐 아니라 Claude Code 어댑터의
`PreCompact`/`SessionStart` 훅과 `/checkpoint-save`, `/resume`, `/handoff`
커맨드까지 제공합니다. 다만 이 경로도 `agent-checkpoint` CLI 자체는
설치하지 않으므로, 스킬이 참조하는 명령이 실행되도록 위 안내대로
`bin/agent-checkpoint`를 `PATH`에 올려두세요.

### npx skills add (Claude Code, Codex, OpenCode 등 `skills` CLI 호환 에이전트)

이 스킬 패키지는 커뮤니티 [`skills`](https://www.npmjs.com/package/skills)
CLI로도 설치할 수 있습니다. 이 CLI는 이 저장소를 클론한 뒤 `skills/`
아래에서 찾은 모든 `SKILL.md`를 에이전트의 스킬 디렉터리에 링크합니다:

```bash
# 모든 checkpoint 스킬 설치
npx skills add https://github.com/man-hy11/agent-checkpoint --all

# 스킬 하나만 설치 (예: 라우터)
npx skills add https://github.com/man-hy11/agent-checkpoint --skill checkpoint
```

이 경로는 스킬 정의만 설치합니다(훅도 커맨드도 없음). `agent-checkpoint`
CLI는 설치되지 않으므로, 스킬이 참조하는 명령이 실행되도록 위 안내대로
`bin/agent-checkpoint`를 `PATH`에 올려두세요.

## 설치 결과물이 위치하는 곳

CLI와 스킬 정의는 독립적으로 설치되는 별개의 두 산출물입니다 — 둘 다
한 번에 설치하는 단일 명령은 없습니다.

### 스킬 파일 (`SKILL.md`)

| 설치 도구 | 실제 파일 위치 | 이름 규칙 |
|---|---|---|
| Claude Code 플러그인 (`/plugin install`) | `~/.claude/plugins/cache/...` | Claude Code가 전적으로 관리; 순수 `SKILL.md` 디렉터리가 아님 |
| `npx skills add ... -g` (커뮤니티 `skills` CLI) | `~/.agents/skills/` | 복수형 `.agents` |

`skills` CLI 경로에서는 지원하는 모든 코딩 에이전트가 원본 사본을
가리키는 심링크를 받습니다 — 에이전트 자신은 사본을 따로 저장하지
않습니다:

```
~/.claude/skills/checkpoint*              -> ~/.agents/skills/checkpoint*
~/.codex/skills/checkpoint*                (또는 $CODEX_HOME/skills)
~/.config/opencode/skills/checkpoint*
```

Gemini CLI는 범용 `SKILL.md` 디렉터리를 전혀 읽지 않으므로, 어느 설치
도구도 Gemini CLI에는 아무것도 링크하지 않습니다.

### 실질적인 영향

CLI와 스킬이 독립적으로 설치되므로, 둘 중 하나만 설치하면 나머지
절반이 빠집니다. 스킬만 설치(Claude Code 플러그인 또는
`npx skills add`)하고 `bin/agent-checkpoint`를 `PATH`에 올리지
않으면, 스킬의 지시가 실행할 수 없는 명령을 참조하게 됩니다.

## 프로젝트 초기화

소비 프로젝트의 루트에서 한 번만 실행하세요:

```bash
agent-checkpoint init
```

초기화는 모든 work package의 `PROGRESS.md`와 `PROGRESS_ARCHIVE.md`
(`.agent-checkpoint/work/*/` 아래)를 무시하는 관리형 블록을 해당
프로젝트의 `.gitignore`에 추가합니다 — 기존 규칙을 대체하지 않습니다.
이 패키지 저장소 자체는 그 이름들을 전역으로 무시하지 않습니다;
초기화가 각 소비 프로젝트에서 개별적으로 제어합니다.

두 진행 파일 중 하나가 이미 추적 중이라면, ignore 규칙만으로는 Git
인덱스에서 제거되지 않습니다. Agent Checkpoint는 라이브 파일과 아카이브
파일 양쪽의 추적/ignore 상태를 검사해 `already tracked` 경고를 내고
수동 Git 마이그레이션은 사용자에게 맡깁니다 — `git rm --cached`를 직접
실행하는 일은 없습니다.

## 핵심 명령어

```bash
agent-checkpoint write --entry checkpoint-entry.md
agent-checkpoint validate --entry checkpoint-entry.md
agent-checkpoint status
agent-checkpoint resume
agent-checkpoint handoff
agent-checkpoint doctor --adapter codex
agent-checkpoint workflow --type feature --id current
```

프로젝트 루트가 현재 디렉터리가 아닐 때는 `--root PATH`를 사용하세요.
`write`, `validate`, `dry-run`은 표준 입력에서 항목을 읽는
`--entry -`를 지원합니다. `resume`과 `handoff`는 `--max-chars NUMBER`를,
`status`와 `doctor`는 `--json`을 지원합니다. `write`, `validate`,
`dry-run`은 Git 또는 unified-diff 형태의 입력을 거부합니다. 쓰기 작업은
기존 라이브 파일이나 아카이브에 안전하지 않은 diff 형태 콘텐츠가
들어가는 것도 거부합니다.

반복된 `write --verification TEXT` 값은 선택적인 `## 6. Verification`
섹션에 저장됩니다. `handoff`는 이렇게 저장된 결과를 `Verification
results` 아래에 렌더링합니다 — `Recent Decisions`에는 포함되지
않습니다.

`doctor`는 체크포인트 상태, Git 추적/worktree 컨텍스트를 확인하고
선택한 어댑터의 기능을 보고합니다. 예:

```bash
agent-checkpoint doctor --adapter claude-code
agent-checkpoint doctor --adapter codex --json
agent-checkpoint doctor --adapter opencode
agent-checkpoint doctor --adapter gemini-cli
```

## 템플릿 기반 work package

번들에는 완전한 개발 템플릿 자산 패키지가 포함돼 있습니다. 새 작업
항목을 시작할 때는 워크플로 타입을 선택해, 해당 타입과 공통 규칙만
소비 프로젝트에 구체화하세요:

```bash
agent-checkpoint workflow --type feature --id current
```

지원하는 타입은 `project`, `feature`, `bugfix`, `refactor`, `upgrade`,
`migration`, `performance`, `integration`, `release`, `spike`입니다.
이 명령은 `.agent-checkpoint/work/current/` 아래에 간결한
`PROGRESS.md` 항목을, 저장소 루트에는 그 패키지를 지목하는
`CONTINUE_PROMPT.md`를 작성합니다. 계획 단계에서 패키지의
`CURRENT.md`와 `PLAN_*.md` 프롬프트를 채우고, 새 세션은 루트
`CONTINUE_PROMPT.md`를 읽은 뒤 패키지의 `CURRENT.md`, 그다음 자체
`CONTINUE_PROMPT.md`를 읽어 Current Target만 실행합니다.

## 프로젝트 설정

소비 프로젝트 루트의 선택적 `.agent-checkpoint.toml`이 기본값을
재정의합니다. `progress_path`/`archive_path`는 활성 work package 기준
상대 경로로 체크포인트 파일명을 지정하며(런타임에
`.agent-checkpoint/work/<id>/` 아래로 재배치됨) 서로 달라야 합니다.
절대 경로, `..`, 제어 문자, 예약된 프로젝트/시스템 경로, 심링크가 낀
경로 구성 요소는 거부됩니다.

```toml
progress_path = "PROGRESS.md"
archive_path = "PROGRESS_ARCHIVE.md"
language = "English"
max_live_chars = 12000
resume_max_chars = 6000
lock_timeout_seconds = 10.0
include_git_hints = true
auto_commit_on_handoff = false
```

`max_live_chars`는 라이브 파일 회전을, `resume_max_chars`는 기본
resume 출력 크기를, `lock_timeout_seconds`는 동시 쓰기 잠금 대기
시간을 제어합니다. `language`는 resume/handoff 지시문으로
렌더링됩니다. `include_git_hints`는 handoff 출력에 안전한 브랜치,
worktree, 변경 파일명 힌트를 포함할지 제어합니다 — 힌트를 꺼도
`doctor`는 여전히 Git 안전 상태를 검사합니다. 체크포인트 콘텐츠와
진단은 자격 증명으로 보이는 텍스트를 거부하며 Git diff는 절대
저장하지 않습니다.

`auto_commit_on_handoff`(기본값 `false`)는 work package의 모든
유닛이 통과한 뒤 `agent-checkpoint handoff`가 끝날 때 작업 트리를
스테이징하고 커밋합니다. handoff 시점 트리의 전체 dirty 상태를
패키지의 변경 범위로 취급합니다 — 유닛 단위 파일 범위 지정은 없습니다.
절대 예외를 던지지 않습니다: Git 저장소가 없거나, 트리가 깨끗하거나,
`git commit`이 실패(예: pre-commit 훅 거부)하는 경우 모두 stderr에
보고되는 스킵으로 처리되며 handoff는 그대로 완료됩니다.

## 개발

전체 테스트 스위트 실행:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

## 라이선스

[MIT License](LICENSE)에 따라 배포됩니다.
