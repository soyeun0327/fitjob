# 06. CI/CD

| 항목 | 내용 |
|---|---|
| 문서 버전 | v0.2 |
| 작성일 | 2026-11-02 |
| 변경 | 개발 기간 온디맨드 운영 반영 (2026-11-02) |
| 변경 | 기존 문제 수정: DB 관리 작업 접속, E2E·보안 회귀 워크플로, RAG 평가 방식 (2026-11-02) |
| 변경 | 수집 전용(`collect_only`) 모드 추가, Phase 2 RDS 상시 이유 명시 (2026-11-02) |
| 변경 | 로컬 개발 도구를 WSL로 통일 (2026-11-03) |
| 도구 | GitHub Actions, AWS (OIDC 인증) |

---

## 1. 저장소 구조 (모노레포)

```
fitjob/
├── app/                 # FastAPI API 서버 (Dockerfile 포함)
├── pipeline/            # Lambda 함수: collector, normalizer, loader, finalizer
├── web/                 # 프론트엔드 (React + Vite 정적 빌드)
├── infra/               # Terraform (modules, stacks 9개, Makefile)
├── tests/
│   ├── e2e/             # Playwright
│   ├── load/            # k6 시나리오
│   └── rag-eval/        # 채팅 평가셋과 실행 스크립트
├── scripts/             # 배포·마이그레이션·스모크·보안 회귀 테스트 스크립트
├── docs/
└── .github/workflows/
```

## 2. 브랜치·커밋 규칙

- **GitHub Flow:** `main` + 기능 브랜치(`feat/…`, `fix/…`, `infra/…`). 모든 변경은 PR로.
- `main` 보호: PR 필수, 필수 상태 검사 통과, 강제 푸시 금지, 선형 히스토리(스쿼시 병합).
- 커밋 메시지: Conventional Commits (`feat:`, `fix:`, `infra:`, `docs:`, `test:`).
- 혼자 개발해도 PR을 쓴다. PR 설명과 plan 댓글이 그대로 작업 기록이 된다.

## 3. 워크플로 목록

| 워크플로 | 트리거 | 하는 일 |
|---|---|---|
| `app-ci.yml` | PR (`app/**`) | 린트(ruff), 타입 검사(mypy), 단위·통합 테스트(pytest + PostgreSQL 서비스 컨테이너), 이미지 빌드, 취약점 스캔(trivy) |
| `app-deploy.yml` | `main` 푸시 (`app/**`) | 이미지 빌드·푸시 → 마이그레이션 → 이미지 태그 갱신 → 인스턴스 새로고침 → 스모크 테스트. `app` 스택이 꺼져 있으면 빌드·푸시와 태그 갱신까지만 ([6.1](#61-순서)) |
| `web-ci.yml` | PR (`web/**`) | 린트, 단위 테스트, 빌드 |
| `web-deploy.yml` | `main` 푸시 (`web/**`) | 빌드 → S3 동기화 → CloudFront 무효화 |
| `pipeline-ci.yml` | PR (`pipeline/**`) | 린트, 정규화 단위 테스트(픽스처), 계약 테스트 |
| `infra-plan.yml` | PR (`infra/**`, `pipeline/**`) | fmt·validate·tflint·checkov, 바뀐 스택별 `plan`, 결과를 PR 댓글로 |
| `infra-apply.yml` | `main` 푸시 (`infra/**`, `pipeline/**`) | 바뀐 상시 스택만 자동 `apply` (GitHub 환경 `prod` 승인 후, `bootstrap` 제외). 온디맨드 스택은 켜져 있을 때만 변경을 apply하고, 꺼져 있으면 건너뛴다 ([8장](#8-인프라-배포)) |
| `drift-check.yml` | 매일 09:00 KST | 상시 스택과 켜져 있는 온디맨드 스택에 `plan -detailed-exitcode`, 변경 있으면 이슈 생성. 개발 기간에는 nightly-down 뒤라 사실상 상시 스택만 점검 |
| `rag-eval.yml` | 운영 단계 매일 08:00 KST, 프롬프트 변경 PR, 수동 실행 | 평가셋 실행, 지표가 기준 미달이면 실패. PR은 **프롬프트 모드**(러너에서 Bedrock 직접 호출, 조건 추출·거절만, 역할 `fitjob-gha-eval`), 예약·수동 실행은 **전체 모드**(배포된 API로 조건 위반까지 모든 자동 지표, AWS 권한 불필요) ([테스트 전략 5.3](07-test-plan.md#53-실행-방식)). 예약 실행은 저장소 변수 `ENV_PHASE`가 `ops`일 때만 돈다 |
| `e2e.yml` | `app-deploy`·`web-deploy` 성공 후(`workflow_run`), 매일 10:00 KST, 수동 실행 | Playwright. 배포 후에는 핵심 시나리오 2개, 매일은 전체 ([테스트 전략 9](07-test-plan.md#9-e2e-테스트-playwright)). 시작할 때 `/api/health`가 200이 아니면 건너뜀. AWS 권한 불필요 |
| `security-smoke.yml` | `infra-apply` 성공 후(`workflow_run`), 매주 월요일 10:30 KST, 수동 실행 | 보안 회귀 스모크 ([테스트 전략 8](07-test-plan.md#8-인프라보안-회귀-테스트)). 읽기 전용 역할 `fitjob-gha-tf-plan`. 환경이 꺼져 있으면 건너뜀 |
| `nightly-down.yml` | 매일 03:00 KST, 수동 실행(`workflow_dispatch`) | `make down`으로 켜진 온디맨드 스택을 끈다. 역할 `fitjob-gha-env-down`. 저장소 변수 `NIGHTLY_DOWN`이 `off`면 건너뜀 ([인프라 명세 12.2](05-infrastructure.md#122-nightly-down)) |

- Lambda 코드는 Terraform `pipeline` 스택이 패키징해 배포한다. 그래서 `pipeline/**` 변경은 infra 워크플로를 탄다.
- 예약 실행 시각은 서로 겹치지 않게 둔다: 03:00 nightly-down → 05:00 수집(개발 기간 `collect_only`, 운영 단계 `full`) → 08:00 RAG 평가(07:00 데이터 갱신 이후) → 09:00 드리프트 점검 → 10:00 E2E(매일) → 10:30 보안 회귀(매주 월요일).
- 환경을 대상으로 하는 예약 테스트(`e2e`, `security-smoke`)는 개발 기간에 환경이 꺼져 있으면 실패가 아니라 건너뜀으로 끝난다.

## 4. 품질 게이트

| 단계 | 통과 기준 | 실패 시 |
|---|---|---|
| 린트·포맷 | 경고 0 | PR 병합 불가 |
| 단위·통합 테스트 | 전부 통과, 정규화 모듈 커버리지 80% 이상 | 병합 불가 |
| 이미지 스캔 | CRITICAL 0 | 병합 불가 |
| 의존성 감사 | `pip-audit`·`npm audit` 고위험 0 (예외는 사유 기록) | 병합 불가 |
| Terraform 정적 분석 | checkov 고위험 0 (예외는 코드에 사유 주석) | 병합 불가 |
| Terraform plan | 사람이 댓글의 plan을 확인하고 승인 | apply 안 함 |
| 스모크 테스트 | `/api/health/deep` 200, 공고 목록 200 | 이전 태그로 자동 롤백 |
| RAG 평가 (PR, 프롬프트 모드) | 조건 추출 정확도 90% 이상, 거절 정확도 100% | 프롬프트 변경 PR 병합 불가 |
| RAG 평가 (예약·수동, 전체 모드) | 조건 위반 0건을 포함한 자동 지표 전부 ([테스트 전략 5.2](07-test-plan.md#52-지표)) | 이슈 생성. 조건 위반이면 S2 결함 |
| E2E·보안 회귀 (예약) | 전부 통과 | 이슈 생성 |

## 5. AWS 인증 (GitHub OIDC)

GitHub Actions가 실행마다 짧은 수명의 토큰으로 IAM 역할을 맡는다. 저장소 시크릿에 AWS 키를 넣지 않는다.

신뢰 정책 예(`fitjob-gha-app-deploy`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<계정ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:<owner>/fitjob:environment:prod"
        }
      }
    }
  ]
}
```

| GitHub 설정 | 값 |
|---|---|
| 저장소 변수 | `APP_DEPLOY_ROLE_ARN`, `WEB_DEPLOY_ROLE_ARN`, `TF_PLAN_ROLE_ARN`, `TF_APPLY_ROLE_ARN`, `EVAL_ROLE_ARN`, `ENV_DOWN_ROLE_ARN`, `DOMAIN` |
| 운영 스위치 변수 | `NIGHTLY_DOWN`(`on`/`off`, 개발 기간 `on`), `ENV_PHASE`(`dev`/`ops`, 운영 단계에 `ops`) |
| 환경 `prod` | 배포 브랜치 `main`만, apply 전 승인 필요 |
| 저장소 시크릿 | 없음 (AWS 키 불필요) |

역할별 권한은 [인프라 명세 5.2](05-infrastructure.md#52-cicd-역할-github-oidc) 참고.

## 6. 앱 배포

### 6.1 순서

| 단계 | 내용 |
|---|---|
| 0. `app` 스택 확인 | ASG `fitjob-prod-app-asg`가 있는지 조회한다. 없으면(개발 기간에 꺼져 있음) 1·3단계만 하고 끝낸다 |
| 1. 빌드·푸시 | 이미지 태그 = git SHA. ECR은 태그 불변이라 같은 태그 덮어쓰기 불가 |
| 2. 마이그레이션 | 러너에서 앱 인스턴스 1대를 거치는 SSM 포트 포워딩으로 RDS에 접속해, 방금 빌드한 새 이미지로 `alembic upgrade head` 실행. 자격증명은 `db-migrator` 시크릿 ([인프라 명세 8.4](05-infrastructure.md#84-db-관리-작업-접속)) |
| 3. 태그 갱신 | SSM 파라미터 `/fitjob/prod/app/image_tag`에 새 SHA 기록 (이전 값은 롤백용으로 보관) |
| 4. 인스턴스 새로고침 | 최소 정상 100%, 최대 정상 200%, 워밍업 180초. 새 인스턴스를 먼저 띄운 뒤 기존 인스턴스를 내리므로 1대 구성에서도 무중단이다. 새 인스턴스는 부팅 시 새 태그를 읽는다 |
| 5. 대기 | 새로고침 상태가 `Successful`이 될 때까지 폴링 (제한 20분) |
| 6. 스모크 테스트 | `/api/health/deep`, `/api/v1/postings?size=1`, `/api/v1/meta/status` |
| 7. 실패 시 롤백 | 태그를 이전 SHA로 되돌리고 새로고침 재실행 |

`app` 스택이 꺼져 있을 때 건너뛴 마이그레이션·새로고침·스모크 테스트는 다음 `make up`이 대신한다. `make up`은 마지막 단계에서 마이그레이션을 실행하고, 새 인스턴스는 부팅할 때 갱신된 태그를 읽는다([인프라 명세 12.1](05-infrastructure.md#121-makefile-타깃)).

### 6.2 롤백을 직접 구현하는 이유

ASG 인스턴스 새로고침의 자동 롤백은 **시작 템플릿 변경**을 되돌리는 기능이다. 이 구조는 시작 템플릿을 그대로 두고 SSM 파라미터의 태그만 바꾸므로, 자동 롤백을 켜도 새 인스턴스가 여전히 새 태그를 읽는다. 그래서 파이프라인이 태그를 되돌리고 새로고침을 다시 시작한다.

대안은 배포마다 태그를 넣은 새 시작 템플릿 버전을 만드는 것이다. 이 경우 자동 롤백은 쓸 수 있지만 Terraform이 관리하는 시작 템플릿과 충돌한다. MVP에서는 파라미터 방식을 쓰고, 이 트레이드오프를 기록해 둔다.

### 6.3 워크플로 예시

```yaml
name: app-deploy

on:
  push:
    branches: [main]
    paths: ["app/**"]

permissions:
  id-token: write
  contents: read

concurrency:
  group: app-deploy
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: prod
    env:
      AWS_REGION: ap-northeast-2
      ECR_REPO: fitjob-api
      IMAGE_TAG: ${{ github.sha }}
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.APP_DEPLOY_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - id: ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Check app stack
        id: app
        run: |
          COUNT=$(aws autoscaling describe-auto-scaling-groups \
            --auto-scaling-group-names fitjob-prod-app-asg \
            --query 'length(AutoScalingGroups)' --output text)
          if [ "$COUNT" -gt 0 ]; then echo "running=true" >> "$GITHUB_OUTPUT"; else echo "running=false" >> "$GITHUB_OUTPUT"; fi

      - name: Build and push
        run: |
          IMAGE="${{ steps.ecr.outputs.registry }}/${ECR_REPO}:${IMAGE_TAG}"
          docker build -t "$IMAGE" app/
          docker push "$IMAGE"

      - name: Save previous tag
        run: |
          PREV=$(aws ssm get-parameter --name /fitjob/prod/app/image_tag --query Parameter.Value --output text)
          echo "PREV_TAG=$PREV" >> "$GITHUB_ENV"

      - name: Migrate database
        if: steps.app.outputs.running == 'true'
        run: ./scripts/run-migration.sh "$IMAGE_TAG"

      - name: Update image tag
        run: aws ssm put-parameter --name /fitjob/prod/app/image_tag --value "$IMAGE_TAG" --type String --overwrite

      - name: Instance refresh
        if: steps.app.outputs.running == 'true'
        run: ./scripts/instance-refresh.sh fitjob-prod-app-asg

      - name: Smoke test
        if: steps.app.outputs.running == 'true'
        run: ./scripts/smoke-test.sh "https://app.${{ vars.DOMAIN }}"

      - name: Roll back on failure
        if: failure() && env.PREV_TAG != '' && steps.app.outputs.running == 'true'
        run: |
          aws ssm put-parameter --name /fitjob/prod/app/image_tag --value "$PREV_TAG" --type String --overwrite
          ./scripts/instance-refresh.sh fitjob-prod-app-asg
```

- 액션 버전은 구현 시점의 최신으로 고정하고, 가능하면 커밋 SHA로 고정한다.
- `run-migration.sh`는 Session Manager 플러그인 설치 → `Stack=app` 인스턴스 1대로 포트 포워딩 세션 시작 → `db-migrator` 시크릿과 DB 주소 조회 → 새 이미지로 `docker run --network host ... alembic upgrade head` → 세션 종료 순서로 동작한다. 앱 서버에는 마이그레이션 자격증명을 주지 않는다.
- 마이그레이션이 성공한 뒤 앱 배포가 실패하면 롤백된 구버전 앱이 새 스키마에서 돈다. 그래서 마이그레이션은 항상 하위 호환으로 작성한다([DB 스키마 11](03-db-schema.md#11-마이그레이션-규칙)).

## 7. 웹 배포

| 단계 | 내용 |
|---|---|
| 빌드 | `npm ci && npm run build` |
| 정적 자산 업로드 | `assets/` (파일명에 해시 포함): `Cache-Control: public, max-age=31536000, immutable` |
| `index.html` 업로드 | `Cache-Control: no-cache` |
| 오래된 파일 정리 | `aws s3 sync --delete` |
| 무효화 | CloudFront `/index.html` |

## 8. 인프라 배포

| 단계 | 내용 |
|---|---|
| PR 생성 | 바뀐 경로로 대상 스택 판별 |
| 정적 검사 | `terraform fmt -check`, `validate`, `tflint`, `checkov` |
| plan | 스택별 `plan` → PR 댓글 (읽기 전용 역할) |
| 검토 | plan에서 삭제·교체되는 리소스가 있으면 PR 설명에 이유 기록 |
| 병합 후 apply | `prod` 환경 승인 → 바뀐 상시 스택(`network`, `storage`, `edge`, `pipeline`)을 의존 순서대로 `apply`. `bootstrap`은 CI 역할을 만드는 스택이라 로컬에서만 apply |
| 온디맨드 스택 | `nat`, `database`, `app`, `observability`는 `make up`으로만 생성한다. 병합 시점에 켜져 있으면(state에 리소스가 있으면) 바뀐 내용만 apply하고, 꺼져 있으면 건너뛴다. 코드는 이미 `main`에 있으므로 다음 `make up` 때 반영된다 |
| 드리프트 점검 | 매일 상시 스택과 켜져 있는 온디맨드 스택에 `plan`으로 수동 변경 감지 |

`network`, `storage`, `database` 스택에서 리소스 **교체**(destroy 후 create)가 plan에 보이면 apply하지 않고 원인을 먼저 확인한다. RDS 교체는 데이터 손실로 이어질 수 있다(`rds_ephemeral = true`로 운영 중이면 replay로 다시 채울 수 있다).

## 9. 로컬 개발

**AWS는 인프라 작업과 통합 확인 때만 켠다.** 앱 개발은 최대한 로컬에서 하고, AWS 환경은 `make up`으로 켰다가 작업이 끝나면 `make down`으로 끈다([인프라 명세 12](05-infrastructure.md#12-온디맨드-운영)).

| 구성 | 방법 |
|---|---|
| 실행 환경 | WSL(Ubuntu). make와 make가 부르는 도구(Terraform, AWS CLI, Session Manager 플러그인, ruff·mypy·pytest 등)는 WSL에 둔다. Docker는 Docker Desktop의 WSL 연동을 쓴다([하네스 2-1](harness.md#2-1-claude-code-권한--claudesettingsjson)) |
| DB | `docker compose`로 PostgreSQL |
| API | `uvicorn` 로컬 실행, `BEDROCK_MODE=stub`이면 LLM·KB 호출을 고정 응답으로 대체 |
| 수집 | 픽스처 파일로 정규화·적재 로직 실행 |
| 실제 Bedrock 테스트 | 개인 IAM 자격증명으로 `BEDROCK_MODE=live` (호출 비용 주의) |
