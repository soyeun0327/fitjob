# FitJob — 하네스 엔지니어링 (Claude Code 기준)

| 항목 | 내용 |
|---|---|
| 문서 버전 | v0.1 |
| 작성일 | 2026-11-02 |
| 변경 | 개발 도구를 WSL로 통일: 권한 패턴을 `wsl -e` 형태로, 훅도 WSL에서 실행 (2026-11-03) |
| 변경 | Phase 0 적용: `.claude/settings.json`(2-1 + 더한 규칙), 링크 검사 스크립트와 `*.md` 훅, 줄바꿈 LF 고정 (2026-11-04) |
| 관련 문서 | [인프라 명세](05-infrastructure.md), [CI/CD](06-cicd.md), [로드맵](09-roadmap.md), [CLAUDE.md](../CLAUDE.md) |

> OpenAI의 하네스 엔지니어링 방법론(https://openai.com/index/harness-engineering/)을 Claude Code 환경에 맞게 옮긴 문서.
> 하네스 = 에이전트가 할 수 있는 것을 **제약(Constrain)**하고, 해야 할 것을 **안내(Inform)**하고, 제대로 했는지 **검증(Verify)**하고, 잘못됐을 때 **교정(Correct)**하는 시스템 전체.

---

## 0. 핵심 원칙

1. **짧은 지도 > 긴 매뉴얼.** CLAUDE.md는 100줄 이내의 "지도"로 유지하고, 상세 내용은 docs/의 개별 문서로 넘긴다. 컨텍스트는 희소 자원이다.
2. **규칙은 기계적으로 강제한다.** "`terraform apply`는 요청할 때만"을 문서에만 쓰지 않고 `.claude/settings.json` 권한으로 막는다. "보안 그룹은 `network` 스택에만"은 구조 테스트로 막는다.
3. **에러 메시지가 곧 교육이다.** 규칙 위반 메시지에 "왜 안 되는지 + 어떻게 고치는지"를 넣어, Claude가 실패 메시지만 보고 스스로 고치게 한다.
4. **에이전트의 반복 실수는 하네스의 버그다.** 같은 유형의 실수가 반복되면 프롬프트를 고치지 않고, 그 실수를 불가능하게 만드는 규칙·훅·테스트를 추가한다. 추가한 것은 [8장](#8-하네스-변경-이력)에 기록한다.
5. **검증할 수 있는 것만 요구한다.** "조건에 맞게 잘 찾아줘"가 아니라 "평가셋에서 조건 위반 0건"처럼 측정할 수 있게 지시하고, 그것을 확인하는 테스트·스크립트를 하네스에 넣는다.

## 1. CLAUDE.md 설계 (지도)

루트 CLAUDE.md는 Claude Code가 매 세션 자동으로 읽는다. **100줄 이내**로 유지하고 다음만 담는다.

- 프로젝트 한 줄 설명과 목적
- 작업 유형별로 반드시 읽을 문서 (링크만)
- 현재 단계와 완료 기록
- 설계 원칙, AWS 작업 규칙, 문서 수정 규칙 (한 줄씩)
- 작업 완료 조건, 명령어, Git 규칙

설명을 덧붙이고 싶어지면 docs/로 옮기고 링크만 남긴다.

**하위 디렉터리 CLAUDE.md.** 해당 디렉터리에서 작업할 때만 읽히므로 컨텍스트를 아낀다. 디렉터리가 생길 때 만든다.

| 파일 | 담을 규칙 |
|---|---|
| `infra/CLAUDE.md` | 이름·태그 규칙, 스택 간 참조 방향, 콘솔 → import 절차 요약([인프라 명세 13](05-infrastructure.md#13-콘솔-구축-후-terraform으로-가져오기)) |
| `app/CLAUDE.md` | 계층 규칙(2-3), LLM 출력 검증, 원문 URL은 RDS 값으로 |
| `pipeline/CLAUDE.md` | 멱등성, 실행 모드(`full`·`collect_only`·`replay`), VPC 밖 Lambda는 DB에 접근하지 않음 |
| `web/CLAUDE.md` | Wanted Design System, Montage 사용 규칙 |

## 2. 기계적 제약 (Constrain)

### 2-1. Claude Code 권한 — `.claude/settings.json`

CLAUDE.md의 "AWS 작업 규칙"을 권한 설정으로 강제한다. `deny`는 항상 막고, `ask`는 실행할 때마다 사용자 승인을 받는다.

개발 도구(make, Terraform, AWS CLI, Session Manager 플러그인, make가 부르는 검사 도구)는 WSL(Ubuntu)에만 둔다. Claude Code의 셸(Git Bash, PowerShell)에서는 `wsl -e <명령>`으로 부른다(예: `wsl -e terraform -chdir=infra/stacks/network plan`). 그래서 패턴도 `wsl` 형태로 쓴다.

```json
{
  "permissions": {
    "deny": [
      "Read(**/.env)",
      "Read(**/*.tfstate)",
      "Read(**/*.tfstate.backup)",
      "Bash(wsl *.tfstate*)",
      "Bash(wsl *terraform*state pull*)",
      "Bash(wsl *secretsmanager get-secret-value*)",
      "Bash(wsl *bash -c*)",
      "Bash(wsl *bash -lc*)",
      "Bash(wsl *sh -c*)",
      "Bash(terraform*)",
      "Bash(aws *)",
      "Bash(make*)",
      "Bash(git push --force*)",
      "Bash(rm -rf*)"
    ],
    "ask": [
      "Bash(wsl *terraform*apply*)",
      "Bash(wsl *terraform*destroy*)",
      "Bash(wsl *terraform*import*)",
      "Bash(wsl *terraform*state *)",
      "Bash(wsl *make*up*)",
      "Bash(wsl *make*down*)",
      "Bash(wsl *aws * create-*)",
      "Bash(wsl *aws * delete-*)",
      "Bash(wsl *aws * put-*)",
      "Bash(wsl *aws * update-*)",
      "Bash(wsl *aws * terminate-*)",
      "Bash(wsl *aws stepfunctions start-execution*)"
    ],
    "allow": [
      "Bash(wsl -e terraform -chdir=* fmt*)",
      "Bash(wsl -e terraform -chdir=* validate*)",
      "Bash(wsl -e terraform -chdir=* plan*)",
      "Bash(wsl -e tflint*)",
      "Bash(wsl -e checkov*)",
      "Bash(wsl -e make check*)",
      "Bash(wsl -e aws * describe-*)",
      "Bash(wsl -e aws * list-*)"
    ]
  }
}
```

**적용 (2026-11-04):** 실제 설정은 [`.claude/settings.json`](../.claude/settings.json)이다. 위 규칙을 Bash·PowerShell 도구에 똑같이 두고, 같은 취지로 아래를 더했다.

| 더한 규칙 | 종류 | 이유 |
|---|---|---|
| `Read(**/.env.*)`, `Read(~/.aws/**)` | deny | 자격증명 파일(`aws login` 캐시 포함)이 대화에 남지 않게 |
| `terraform show -json`, `--with-decryption` | deny | state와 SecureString 파라미터의 비밀값을 그대로 출력한다 |
| `git push -f` 변형 | deny | `--force`만 막으면 `-f` 표기로 우회된다 |
| `terraform force-unlock`·`taint`·`output`·`-migrate-state` | ask | state를 바꾸거나 출력값(비밀값 포함 가능)을 보여준다 |
| AWS `run-`·`start-`·`stop-`·`modify-`·`attach-`·`detach-`·`associate-`·`authorize-`·`revoke-`·`tag-`·`invoke`, `s3 cp·mv·rm·rb·mb·sync`, `configure`, `login` | ask | 리소스를 바꾸거나 비용이 드는 명령. CLAUDE.md "AWS 쓰기 명령은 요청할 때만" |
| `wsl -u root`, `sudo` | ask | 관리자 권한 실행 |
| `git push`, `git reset --hard`, `git clean` | ask | 푸시는 요청할 때만, 파괴적 작업은 한 번 더 확인(CLAUDE.md Git 규칙) |
| `terraform version`, `aws * get-*`, 링크 검사 스크립트 | allow | 읽기 전용. `get-secret-value`와 `--with-decryption`은 deny가 먼저 걸린다 |

- **실행 형태는 `wsl -e <명령>`으로 고정한다.** `-e`는 리눅스 셸을 거치지 않고 명령을 바로 실행한다. `wsl bash -c "…"`처럼 명령을 문자열로 넘기면 그 안에 무엇이 들었든 권한 검사가 한 덩어리로 보므로 deny로 막는다.
- **Windows에서 terraform·aws·make를 직접 실행하지 않는다(deny).** 같은 폴더를 Windows Terraform과 WSL Terraform이 번갈아 쓰면 `.terraform/`의 프로바이더 파일이 OS별로 달라 꼬인다.
- **deny·ask는 넓게(`wsl *…*`), allow는 좁게(`wsl -e …`) 쓴다.** 한 명령이 여러 규칙에 걸리면 deny → ask → allow 순으로 적용되므로 넓은 ask가 좁은 allow보다 우선한다. 넓은 패턴 때문에 읽기 명령을 가끔 묻게 되는 것은 안전한 쪽의 오탐이라 받아들인다.
- **경로는 상대 경로로 준다.** `wsl`은 셸의 현재 폴더(저장소 루트)를 그대로 이어받는다. Git Bash는 `/`로 시작하는 인자를 Windows 경로로 바꾸므로(`/mnt/c/x` → `C:/Program Files/Git/mnt/c/x`) 절대 경로를 쓰면 엉뚱한 곳을 가리킨다.
- state 파일에는 비밀값(예: 오리진 검증 헤더 값)이 들어 있어 읽기를 막는다(`Read`, `.tfstate` 파일, `state pull`). 시크릿 값 조회도 막아 대화에 비밀값이 남지 않게 한다.
- PowerShell 도구에도 같은 규칙을 둔다.
- 패턴 문법(중간 `*` 등)은 적용할 때 Claude Code의 `/permissions`로 실제로 걸리는지 확인한다.

### 2-2. Terraform 규칙 — tflint, checkov, 구조 테스트

tflint·checkov로 잡히는 것은 그 도구로, 이 프로젝트 고유 규칙은 구조 테스트(`scripts/check_infra_rules.py`, HCL을 읽어 검사)로 막는다.

| 규칙 | 막는 것 | 에러 메시지에 넣을 교정 지침 |
|---|---|---|
| `required-tags` | `Project`·`Env`·`ManagedBy`·`Stack` 태그 누락 | "provider `default_tags`에 태그 4개를 두세요. 인프라 명세 1장 참고" |
| `naming` | `fitjob-prod-<역할>`이 아닌 이름 | "리소스 이름은 `fitjob-prod-<역할>`, 버킷은 `fitjob-prod-<용도>-<계정ID>`" |
| `no-ssh` (checkov) | 22번 포트 인바운드 | "22번은 열지 않습니다. 접속은 SSM Session Manager로 하세요" |
| `sg-in-network-only` | `network` 밖의 `aws_security_group` | "보안 그룹은 `network` 스택에 두고, 다른 스택은 remote_state로 ID를 읽으세요. 온디맨드 스택에 두면 destroy가 의존성 오류로 멈춥니다" |
| `secrets-in-storage-only` | `storage` 밖의 `aws_secretsmanager_secret` | "시크릿은 상시 `storage` 스택에 두세요. 지우면 복구 대기 기간 동안 같은 이름으로 다시 만들 수 없습니다" |
| `no-ondemand-ref` | 상시 스택이 `nat`·`database`·`app`·`observability`의 remote_state를 참조 | "상시 스택은 온디맨드 스택을 참조하지 않습니다. SSM 파라미터로 넘기고 실행할 때 읽으세요" |
| `no-inline-route` | `network`의 `aws_route_table` 안 `route` 블록 | "경로는 `aws_route` 리소스로 만드세요. 인라인으로 쓰면 `network` apply가 `nat` 스택의 경로를 지웁니다" |
| `no-secret-value` | 시크릿 값이 든 `variable` 기본값·tfvars, `aws_secretsmanager_secret_version` import | "시크릿은 틀만 Terraform으로 만들고 값은 CLI로 넣으세요" |

### 2-3. Python 계층 규칙 — import-linter

계층 구조는 구현을 시작할 때 확정한다. 지금 정해 둘 규칙:

| 규칙 | 막는 것 | 에러 메시지에 넣을 교정 지침 |
|---|---|---|
| `outside-vpc-no-db` | `pipeline/collector`, `pipeline/normalizer`가 DB 드라이버(psycopg, SQLAlchemy) import | "수집·정규화 Lambda는 VPC 밖이라 RDS에 닿지 않습니다. DB 쓰기는 loader에서 하세요" |
| `bedrock-via-llm` | `app/llm/` 밖에서 Bedrock 런타임 직접 호출 | "LLM 호출은 `app/llm/`을 거치세요. 도구 스키마 검증과 실패 시 대체 응답이 거기에 있습니다" |
| `layer-order` | 하위 계층 → 상위 계층 역참조 (예: repository → api) | "의존 방향은 api → services → repositories·llm 입니다" |

### 2-4. 문서 규칙

| 규칙 | 막는 것 | 방법 |
|---|---|---|
| 링크·앵커 | 깨진 상대 링크, 없는 섹션 앵커 | `scripts/check_doc_links.py`가 GitHub 앵커 규칙으로 검사 |
| 숫자 일치 | 문서마다 다른 비용·ASG 대수·스택 수·시크릿 수·워크플로 수·일정 | 기준값을 `docs/facts.yaml` 한 곳에 두고, 문서에 다른 값이 나오면 실패 |

## 3. 검증 루프 (Verify) — Claude Code 훅

`.claude/settings.json`의 hooks로 검증을 자동으로 돌린다. 사람이 "검사해 봐"라고 말할 필요가 없게 하는 것이 목표다.

| 훅 | 시점 | 동작 |
|---|---|---|
| PostToolUse (Edit/Write, `*.tf`) | 수정 직후 | `terraform fmt` + 해당 스택 `terraform validate` + 구조 테스트. 실패하면 메시지를 Claude에 돌려줘 바로 고치게 한다 |
| PostToolUse (Edit/Write, `*.py`) | 수정 직후 | `ruff check --fix`, `ruff format`, 해당 패키지 import-linter |
| PostToolUse (Edit/Write, `*.md`) | 수정 직후 | 링크·앵커 검사, 숫자 일치 검사 |
| PreToolUse (Bash) | 실행 전 | 권한 패턴으로 못 막는 조건부 규칙. 예: `rds_ephemeral = false`인데 `database` 스택 destroy면 차단 |
| Stop | 응답 끝 | 바뀐 영역의 `make check` 실행. 통과 전에는 작업 완료로 치지 않는다 |

`make check`는 영역별 검사를 묶은 타깃이다: 인프라(fmt·validate·tflint·checkov·구조 테스트), 앱·파이프라인(ruff·mypy·import-linter·pytest), 문서(링크·숫자). CI도 같은 명령을 쓴다.

훅이 부르는 terraform·make도 [2-1](#2-1-claude-code-권한--claudesettingsjson)과 같이 WSL에서 실행한다(`wsl -e …`).

## 4. 관측 가능성 (Observe)

Claude가 결과를 직접 확인할 수단을 하네스에 넣는다.

| 수단 | 무엇을 확인 |
|---|---|
| `terraform plan -detailed-exitcode` | 코드와 실제가 같은지(import 후 "No changes", 드리프트) |
| 읽기 전용 AWS 조회 | `describe`·`list`, 태그 검색(`Stack`, `ManagedBy=console`)으로 남은 리소스 |
| `/api/health/deep`, `/api/v1/meta/status` | DB·외부 통신 상태, 데이터 기준 시각, 공고 수 |
| 개발 전용 디버그 엔드포인트 `GET /api/debug/filters?message=...` | 조건 추출 결과와 그것을 바꾼 KB 필터·SQL을 JSON으로. 하드 조건이 필터로 들어갔는지 한 번에 확인 (개발 모드에서만) |
| Step Functions 실행 기록 | 파이프라인 단계별 성공·실패, 모드별 결과 |
| CloudWatch Logs Insights | [운영 문서 3.1](08-operations.md#31-로그)의 쿼리 재사용 |
| Cost Explorer 조회 | 어제 비용을 `Stack` 태그별로, 켜져 있는 온디맨드 스택 확인 |
| RAG 평가 결과 파일 | 조건 위반률·추출 정확도 추이 |
| 로컬 실행 | docker compose + `BEDROCK_MODE=stub`로 API를 띄워 curl로 확인 |

## 5. 작업 단위와 명령 (Inform)

### 5-1. 실행 계획

[로드맵](09-roadmap.md) 3장의 Phase별 표에서 한 행이 하나의 작업 단위다. Claude에게는 "Phase 1의 `network` 행을 진행해"처럼 행 단위로 지시한다. 각 Phase의 완료 기준은 검증할 수 있는 형태("`plan` No changes", "3일 연속 성공")로 적혀 있어야 한다. 한 행이 너무 크면 `docs/plans/phase-N.md`로 나눈다.

### 5-2. 슬래시 커맨드 — `.claude/commands/`

| 커맨드 | 내용 |
|---|---|
| `/verify` | 바뀐 영역의 `make check` 실행 후 결과 요약 |
| `/plan-status` | 로드맵과 CLAUDE.md 완료 기록을 읽고 현재 Phase의 완료·미완료 항목 정리 |
| `/import-check <스택>` | 해당 스택 `plan`이 "No changes"인지, `ManagedBy=console` 리소스가 남았는지 |
| `/cost-check` | 어제 비용(`Stack` 태그별), 켜져 있는 온디맨드 스택, 잊고 켜둔 리소스 |
| `/doc-sync` | 문서 간 숫자·이름 일치와 링크 검사 |

### 5-3. 서브에이전트 — `.claude/agents/`

| 이름 | 역할 |
|---|---|
| `reviewer` | 변경 diff를 CLAUDE.md 설계 원칙과 2장 규칙 관점에서 검토. 읽기 전용 |
| `plan-reader` | 긴 `terraform plan` 출력을 요약하고 교체·삭제되는 리소스를 강조. 긴 출력이 메인 컨텍스트를 차지하지 않게 격리 |
| `e2e-runner` | Playwright·RAG 평가 실행과 실패 분석. 긴 로그를 격리 |

## 6. 엔트로피 관리 (Correct)

에이전트는 저장소에 이미 있는 패턴을 따라 한다. 나쁜 패턴이 하나 들어오면 늘어난다.

- **좋은 예·나쁜 예:** 코드가 생기면 `docs/conventions.md`에 쌍으로 둔다. 예: 인라인 `route` vs `aws_route`, 하드코딩한 ID vs remote_state·SSM 파라미터, Bedrock 직접 호출 vs `app/llm/` 경유
- **문서와 코드의 불일치 점검:** DB 스키마 문서 vs Alembic, 인프라 명세 vs Terraform, API 명세 vs `openapi.json`. 처음에는 `/doc-sync`로 손으로 돌린다. 주기 실행(`claude -p`를 GitHub Actions 예약 실행)은 운영 단계 이후 선택이고, 도입하면 [CI/CD 3장](06-cicd.md#3-워크플로-목록) 목록과 워크플로 개수를 갱신한다
- **1인 운영 현실:** 정리 PR은 자동 머지하지 않고 직접 리뷰한 뒤 머지한다
- **실수 → 규칙 전환 기록:** Claude가 저지른 실수와 그에 맞춰 추가한 규칙을 8장에 남긴다. 같은 실수가 다시 나오면 규칙이 부족하다는 신호다

## 7. 단계별 구축 순서

처음부터 전부 갖추지 않는다. Phase마다 필요한 만큼만 만든다.

| 단계 | 갖출 것 |
|---|---|
| **Phase 0** (W1) | CLAUDE.md(지도), `.claude/settings.json` 권한(2-1), 문서 링크 검사 스크립트와 `*.md` PostToolUse 훅, `.gitattributes`·`.editorconfig`로 줄바꿈 LF 고정. 2026-11-04에 모두 적용했다 |
| **Phase 1** (W2~4) | `*.tf` PostToolUse 훅(fmt·validate), tflint·checkov 기본, 구조 테스트 `sg-in-network-only`·`no-inline-route`·`required-tags`, `/import-check`, `infra/CLAUDE.md` |
| **Phase 2** (W5~6) | `*.py` 훅(ruff), import-linter `outside-vpc-no-db`, 구조 테스트 `no-ondemand-ref`·`secrets-in-storage-only`, `plan-reader` 서브에이전트 |
| **Phase 3** (W7~9) | 앱 계층 규칙(`bedrock-via-llm`, `layer-order`), 디버그 엔드포인트, `make check`와 Stop 훅, `/cost-check` |
| **Phase 4~5** (W10~11) | CI에서 같은 검사 실행, `reviewer` 서브에이전트, 문서 숫자 일치 검사(`docs/facts.yaml`)와 `/doc-sync` |
| **Phase 6 이후** | 문서·코드 불일치 주기 점검(선택), 8장 변경 이력 운영 |

> 원칙: 하네스도 점진적으로. "Claude가 실수하면 → 그 실수를 막는 규칙을 추가"하는 습관을 Phase 0부터 들이는 것이 문서를 완벽하게 갖추는 것보다 중요하다.

## 8. 하네스 변경 이력

| 날짜 | Claude의 실수 | 추가한 규칙·훅 |
|---|---|---|
| (아직 없음) | | |
