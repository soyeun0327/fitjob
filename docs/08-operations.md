# 08. 운영 · 모니터링 · 런북

| 항목 | 내용 |
|---|---|
| 문서 버전 | v0.2 |
| 작성일 | 2026-11-02 |
| 변경 | 개발 기간 온디맨드 운영 반영 (2026-11-02) |
| 변경 | 기존 문제 수정: DB 관리 작업 접속, E2E·보안 회귀 워크플로, RAG 평가 방식 (2026-11-02) |
| 변경 | 수집 전용(`collect_only`) 모드 추가, Phase 2 RDS 상시 이유 명시 (2026-11-02) |
| 변경 | 콘솔 구축 후 Terraform으로 가져오는 방식(ADR-012), 일정 14주 (2026-11-02) |
| 관련 문서 | [아키텍처](02-architecture.md), [인프라 명세](05-infrastructure.md), [테스트 전략](07-test-plan.md) |

---

## 1. 서비스 수준 목표 (SLO)

**SLO는 24시간 운영하는 운영 단계(W12~14)에만 적용한다.** 개발 기간에는 온디맨드 스택을 작업할 때만 켜므로 가용성·지연·신선도를 재지 않는다([ADR-011](10-adr.md#adr-011-개발-기간에는-비싼-리소스를-온디맨드로-운영한다)).

| SLI | 정의 | SLO |
|---|---|---|
| 가용성 | `/api/v1/*` 요청 중 5xx가 아닌 비율 | 월 99.0% (오류 예산 약 7.2시간) |
| 채팅 지연 | 앱 지표 `ChatLatency` p95 | 6초 이하 |
| 목록 지연 | 앱 지표 `RequestLatency`(route=postings) p95 | 500ms 이하 |
| 데이터 신선도 | 매일 07:00까지 수집 실행이 `SUCCEEDED` 또는 `PARTIAL`로 완료 | 월 95% 이상의 날 |

오류 예산을 다 쓰면 그달은 기능 추가를 멈추고 안정화 작업만 한다.

## 2. 대시보드

CloudWatch 대시보드 `fitjob-prod` 하나에 아래 영역을 둔다. 대시보드는 `observability` 스택에 있어 운영 단계에만 켠다.

| 영역 | 위젯 |
|---|---|
| 서비스 | 요청 수, 5xx 수, ALB 응답 시간 p95, 정상 대상 수 |
| 채팅 | `ChatLatency` p50·p95, 응답 상태 분포(OK·NO_RESULT·DEGRADED·REFUSED), 일별 채팅 수, Bedrock 입력·출력 토큰 |
| 컴퓨팅 | ASG 서비스 중 인스턴스 수, 인스턴스별 CPU·CPU 크레딧 |
| 네트워크 | NAT 인스턴스 CPU·네트워크 입출력·상태 검사 |
| 데이터베이스 | RDS CPU, 연결 수, 여유 메모리, 여유 스토리지 |
| 파이프라인 | 실행 성공·실패, 소스별 수집 건수, 격리 건수, KB 문서 쓰기·삭제 건수 |

## 3. 로그와 지표

### 3.1 로그

| 로그 그룹 | 내용 | 보존 |
|---|---|---|
| `/fitjob/prod/api` | 앱 JSON 로그 ([API 명세 9](04-api-spec.md#9-로그와-지표)) | 30일 |
| `/aws/lambda/fitjob-prod-*` | 파이프라인 Lambda 로그 | 30일 |
| `/aws/vendedlogs/states/fitjob-prod-ingest` | Step Functions 실행 로그 | 30일 |

자주 쓰는 Logs Insights 쿼리:

```text
# 최근 5xx
fields @timestamp, request_id, method, path, status, latency_ms
| filter status >= 500
| sort @timestamp desc
| limit 50
```

```text
# 채팅 5분 단위 p95와 건수
filter path = "/api/v1/chat"
| stats pct(latency_ms, 95) as p95, count(*) as chats by bin(5m)
```

```text
# 대체 응답(DEGRADED) 원인
filter chat_status = "DEGRADED"
| stats count(*) by error_type
```

### 3.2 사용자 지표 (네임스페이스 `FitJob`)

| 지표 | 차원 | 보내는 곳 |
|---|---|---|
| `RequestLatency` | route | API (EMF) |
| `ChatLatency` | status | API (EMF) |
| `BedrockInputTokens`, `BedrockOutputTokens` | step(extract, reason) | API (EMF) |
| `ZeroResultChats`, `DegradedResponses` | | API (EMF) |
| `PipelineSucceeded` | | 마무리 Lambda (성공 시 1) |
| `FetchedCount`, `QuarantinedCount` | source | 정규화 Lambda |

## 4. 알람

심각도: **P1** 핵심 기능 중단(즉시 확인) · **P2** 당일 조치 · **P3** 주중 조치

**알람이 언제 동작하는지:**

| 알림 | 스택 | 동작 기간 |
|---|---|---|
| AWS Budgets 비용 알림 | `bootstrap` (상시) | 항상 |
| Step Functions 실패 처리 단계가 직접 보내는 수집·KB 동기화 실패 알림 | `pipeline` (상시) | 파이프라인이 실행될 때 항상 (개발 기간에는 매일 05:00 `collect_only`) |
| nightly-down 실패 메일 | GitHub Actions | 개발 기간 |
| 그 밖의 CloudWatch 알람, Route 53 헬스체크 알람 | `observability` (온디맨드) | 운영 단계에만 |

| 알람 | 지표 | 조건 | 심각도 | 런북 |
|---|---|---|---|---|
| 서비스 외부 경로 이상 | Route 53 헬스체크 `HealthCheckStatus` | 3회 연속 실패 | P1 | RB-01 |
| 정상 대상 없음 | ALB `HealthyHostCount` | 1 미만, 2분 | P1 | RB-02 |
| NAT 상태 검사 실패 | EC2 `StatusCheckFailed` (NAT) | 1 이상, 2분 | P1 | RB-01 |
| 5xx 증가 | ALB `HTTPCode_Target_5XX_Count` | 5분 합계 10 이상 | P2 | RB-02 |
| 채팅 대체 응답 증가 | `DegradedResponses` / 채팅 수 | 10분간 20% 초과 | P2 | RB-07 |
| 수집 실행 실패 | Step Functions `ExecutionsFailed` | 1 이상 | P2 | RB-03 |
| 수집 미완료 | `PipelineSucceeded` | 24시간 합계 1 미만 (누락은 위반으로 처리) | P2 | RB-03 |
| KB 동기화 실패 | Step Functions 실패 처리 단계가 SNS로 직접 발행 | 발생 시 | P2 | RB-04 |
| RDS 스토리지 부족 | RDS `FreeStorageSpace` | 2GB 미만 | P2 | RB-05 |
| 비정상 대상 | ALB `UnHealthyHostCount` | 1 이상, 5분 | P3 | RB-02 |
| 응답 지연 | ALB `TargetResponseTime` p95 | 6초 초과, 10분 | P3 | RB-02 |
| 확장 한계 | ASG `GroupInServiceInstances` | 최대값(4)과 같음, 15분 | P3 | RB-02 |
| CPU 크레딧 고갈 | EC2 `CPUCreditBalance` (앱) | 20 미만, 30분 | P3 | RB-02 |
| RDS 부하 | RDS `CPUUtilization` | 80% 초과, 15분 | P3 | RB-05 |
| RDS 연결 과다 | RDS `DatabaseConnections` | 최대 연결의 80% 초과 | P3 | RB-05 |
| Bedrock 쓰로틀 | Bedrock `InvocationThrottles` | 5분 합계 5 이상 | P3 | RB-07 |
| 수집 건수 급감 | `FetchedCount` | 7일 평균의 50% 미만 | P3 | RB-03 |
| 격리 비율 증가 | `QuarantinedCount` / `FetchedCount` | 5% 초과 | P3 | RB-03 |
| 비용 | AWS Budgets (`bootstrap`) | 실제 50·80·100%, 예측 100% | P2 | RB-06 |
| 온디맨드 스택 끄기 실패 | GitHub Actions `nightly-down` 실패 알림 메일 | 발생 시 | P2 | RB-08 |

- 모든 알람은 `bootstrap` 스택의 공용 SNS 토픽 `fitjob-prod-alerts` → 이메일로 보낸다. 복구(OK) 알림도 받는다.
- **Route 53 헬스체크 지표는 us-east-1에만 있다.** 그래서 이 알람과 연결할 SNS 토픽(`fitjob-prod-alerts-use1`)을 us-east-1에 따로 만든다.

## 5. 런북

각 런북은 증상 → 확인 → 조치 → 사후 순서로 따른다. 조치는 원칙적으로 Terraform이나 배포 파이프라인으로 하고, 콘솔에서 고친 것은 반드시 코드에 반영한다.

명령에 나오는 `$SFN_ARN`, `$TG_ARN`, `$KB_ID`, `$DS_ID`는 각 스택의 Terraform output 값이다. `scripts/ops-env.sh`가 이 값을 환경 변수로 내보내도록 만들어 두고, 런북을 시작할 때 `source scripts/ops-env.sh`를 먼저 실행한다.

### RB-01 채팅 장애 · 외부 호출 실패 (NAT 의심)

**증상:** deep 헬스체크 실패(`egress: fail`), 채팅이 `DEGRADED`, 목록은 정상

1. NAT 인스턴스 상태 확인
   ```bash
   aws ec2 describe-instances \
     --filters "Name=tag:Name,Values=fitjob-prod-nat" \
     --query "Reservations[].Instances[].[InstanceId,State.Name]" --output table
   ```
2. 앱 라우팅 테이블의 기본 경로 상태 확인 (`blackhole`이면 대상이 사라진 것)
   ```bash
   aws ec2 describe-route-tables \
     --filters "Name=tag:Name,Values=fitjob-prod-rt-app" \
     --query "RouteTables[].Routes[?DestinationCidrBlock=='0.0.0.0/0']" --output table
   ```
3. Session Manager로 앱 인스턴스에 접속해 외부 통신 확인
   ```bash
   curl -m 5 -s https://checkip.amazonaws.com || echo "egress failed"
   ```

**조치**
- 1단계(직접 구성 NAT): `infra/stacks/nat`에서 `terraform apply`로 NAT 인스턴스와 경로를 다시 만든다. 콘솔에서 수동으로 만들지 않는다.
- 2단계(fck-nat): ASG 활동 기록에서 새 인스턴스가 떴는지, 고정 ENI가 붙었는지 확인한다. 반복해서 실패하면 시작 템플릿·AMI를 점검한다.

**사후:** 장애 보고서 작성. 감지·복구 시간을 GD-01 결과와 비교한다.

### RB-02 5xx 증가 · 비정상 대상 · 응답 지연

1. 최근 배포가 있었는지 확인 (GitHub Actions `app-deploy` 기록). 있으면 이전 태그로 롤백:
   ```bash
   aws ssm put-parameter --name /fitjob/prod/app/image_tag --value "$PREV_SHA" --type String --overwrite
   ./scripts/instance-refresh.sh fitjob-prod-app-asg
   ```
2. 대상 상태 확인
   ```bash
   aws elbv2 describe-target-health --target-group-arn "$TG_ARN" --output table
   ```
3. Logs Insights로 5xx 요청과 예외 확인 ([3.1](#31-로그))
4. CPU·CPU 크레딧이 원인이면 ASG 최대값을 임시로 올리고, 인스턴스 타입 변경을 검토한다.
5. DB 오류가 원인이면 RB-05.

### RB-03 수집 파이프라인 실패 · 미완료 · 이상 수치

1. 실패한 실행 찾기
   ```bash
   aws stepfunctions list-executions --state-machine-arn "$SFN_ARN" \
     --status-filter FAILED --max-items 5
   ```
2. 실패 단계와 오류 확인: 콘솔의 실행 그래프 또는 `get-execution-history`, 해당 Lambda 로그
3. 원인별 조치

| 원인 | 조치 |
|---|---|
| API 키 만료·오류 | Secrets Manager `fitjob/prod/api-keys` 갱신 |
| 호출 한도 초과 | 페이지 크기·호출 간격 조정, 소스에 한도 문의 |
| 응답 형식 변경(계약 테스트 실패) | 픽스처·스키마·정규화 코드 수정 PR |
| 적재 실패(DB) | RB-05 확인 후 replay로 적재부터 재실행 |
| 개발 기간에 `nat`·`database`가 꺼진 상태로 `full`·`replay`를 실행함 | `make up`(또는 `make up-app`) 후 replay로 재실행. 개발 중 예약 실행은 `schedule_mode = collect_only`여야 한다(`full`이면 05:00마다 적재가 실패) |
| `collect_only` 실행 실패 | 수집·정규화 단계 문제다. 위 API 키·호출 한도·응답 형식 행을 따른다. RDS·NAT와는 관계없다 |

4. 같은 기준일로 재실행 (적재는 멱등이라 중복이 생기지 않는다). 수집·정규화는 성공했고 적재 이후만 실패했다면 replay 모드로 적재부터 다시 실행한다([DB 스키마 6.6](03-db-schema.md#66-재적재replay)).
   ```bash
   # 처음부터 다시
   aws stepfunctions start-execution --state-machine-arn "$SFN_ARN" \
     --name "rerun-2026-11-02-01" --input '{"run_date": "2026-11-02"}'

   # 적재부터 다시 (S3 staging/ 사용)
   aws stepfunctions start-execution --state-machine-arn "$SFN_ARN" \
     --name "replay-2026-11-02-01" --input '{"mode": "replay", "run_date": "2026-11-02"}'
   ```
5. 수집 건수 급감 알람이면 소스 사이트에서 공고 수를 눈으로 비교한다. 이 경우 해당 소스의 마감 처리는 자동으로 건너뛰었는지 `ingestion_source_stats.closed_count`로 확인한다.

### RB-04 KB 동기화 실패

1. 실패 사유 확인
   ```bash
   aws bedrock-agent get-ingestion-job --knowledge-base-id "$KB_ID" \
     --data-source-id "$DS_ID" --ingestion-job-id "$JOB_ID"
   ```
2. 문서 형식·메타데이터 오류면 적재 Lambda의 문서 생성 로직을 고친다.
3. 동기화 재실행
   ```bash
   aws bedrock-agent start-ingestion-job --knowledge-base-id "$KB_ID" --data-source-id "$DS_ID"
   ```
4. 동기화가 늦어도 채팅 결과는 RDS에서 마감 공고를 걸러내므로 긴급도는 P2다.

### RB-05 RDS 문제

| 증상 | 확인 | 조치 |
|---|---|---|
| 스토리지 부족 | `FreeStorageSpace`, 큰 테이블 | 보존 정책 삭제가 돌았는지 확인, 필요하면 스토리지 증설 |
| 연결 과다 | `DatabaseConnections`, 앱 연결 풀 설정 | 인스턴스당 풀 크기 축소, 누수 확인 |
| CPU 높음 | 느린 쿼리 로그(500ms 이상) | 인덱스 추가(마이그레이션으로) |
| 인스턴스 장애 | RDS 이벤트 | 자동 복구 대기, 장기화되면 시점 복구 |

시점 복구 절차(요지, GD-07에서 다듬는다):
1. 복구 시각을 정하고 새 식별자로 시점 복구 인스턴스 생성
2. 행 수·최근 데이터로 검증
3. 앱이 쓰는 DB 엔드포인트를 새 인스턴스로 교체
4. Terraform state에 새 인스턴스 반영(import), 이전 인스턴스는 스냅샷 후 정리

### RB-06 비용 급증

1. Cost Explorer에서 서비스별·`Project` 태그별로 어제 비용 확인
2. 흔한 원인

| 원인 | 확인 | 조치 |
|---|---|---|
| Bedrock 토큰 급증(남용) | `BedrockInputTokens` 추이, IP별 채팅 수 | `/fitjob/prod/app/chat_daily_limit` 하향(앱이 5분 내 반영), 필요하면 WAF 도입 |
| ASG 최대치 유지 | ASG 활동 | 원인 트래픽 확인, 최대값 조정 |
| 꺼지지 않은 온디맨드 리소스 | nightly-down 실행 기록, `Stack` 태그 검색 | RB-08 |
| 잊어버린 리소스 | 태그 없는 리소스, 미사용 EIP·스냅샷 | 삭제 후 코드 반영 |
| 데이터 전송 | NAT 네트워크, CloudFront | 대용량 전송 원인 확인 |

### RB-07 Bedrock 쓰로틀링 · 오류

1. `InvocationThrottles`, `InvocationServerErrors` 확인
2. 서비스 할당량(Service Quotas)에서 모델별 분당 요청·토큰 한도 확인, 필요하면 증설 요청
3. 임시 완화: `/fitjob/prod/app/reasons_mode`를 `template`로 바꾼다(앱이 5분 내 반영). 매칭 이유는 공고 필드로 만든 템플릿 문장으로 계속 표시되고, 채팅당 LLM 호출이 2회에서 1회로 줄어 조건 추출에 한도를 남긴다([API 명세 5.4](04-api-spec.md#54-매칭-이유-생성))
   ```bash
   aws ssm put-parameter --name /fitjob/prod/app/reasons_mode --value template --type String --overwrite
   ```
4. 장애가 길면 채팅은 자동으로 `DEGRADED` 응답을 유지한다. 이때도 결과의 매칭 이유는 템플릿으로 채워진다
5. 복구 후: 쓰로틀 지표가 30분 이상 0이면 `reasons_mode`를 `llm`으로 되돌린다. 쓰로틀링이 반복되면 할당량 증설이나 교차 리전 추론 프로필 적용을 검토하고, 사유를 ADR에 남긴다

### RB-08 make up/down 실패 · 꺼지지 않은 리소스

**증상:** `make up`·`make down`이 오류로 멈춤, nightly-down 실패 메일 수신, 다음 날 Cost Explorer에 밤사이 ALB·EC2·RDS 비용이 보임

**`make down`이 의존성 오류로 멈출 때 확인 순서**

1. `make` 출력에서 멈춘 스택과 리소스를 확인한다. 끄는 순서는 `observability` → `app` → `database` → `nat`다.
2. 그 스택에 남은 리소스를 본다.
   ```bash
   terraform -chdir=infra/stacks/<스택> state list
   ```
3. 원인별 조치

| 원인 | 조치 |
|---|---|
| 상시 스택 리소스가 온디맨드 리소스를 참조(예: 콘솔에서 보안 그룹 규칙을 손으로 추가) | 참조를 지우고 해당 상시 스택 코드에 반영. 보안 그룹은 모두 `network`에 있어야 한다 |
| ALB·ENI 삭제가 끝나지 않음 | 몇 분 기다린 뒤 `make down` 재실행 (destroy는 다시 실행해도 안전하다) |
| `database` destroy가 삭제 보호로 실패 | `rds_ephemeral = false`인데 `database`를 지우려 한 경우다. `make down`이 건너뛰는지 확인하고, 정말 지우려면 `rds_ephemeral = true`로 apply한 뒤 다시 실행 |
| state 잠금(lock)이 남음 | 다른 실행(nightly-down과 수동 실행이 겹침 등)이 끝났는지 확인한 뒤 `terraform force-unlock` |

4. 같은 명령으로 다시 실행한다. 그래도 안 되면 남은 리소스를 CLI로 지우고 `terraform state rm`으로 state를 맞춘 뒤, 원인을 코드에 반영한다.

**남은 리소스 찾기**

```bash
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Stack,Values=nat,database,app,observability \
  --query "ResourceTagMappingList[].ResourceARN" --output table

# Route 53 헬스체크 알람·SNS 토픽처럼 us-east-1에 있는 observability 리소스
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Stack,Values=observability \
  --query "ResourceTagMappingList[].ResourceARN" --output table
```

결과가 비어 있어야 정상이다. 태그 API는 방금 지운 리소스를 잠시 보여줄 수 있으므로, 나온 리소스는 해당 서비스 콘솔이나 CLI에서 실제로 남아 있는지 확인한다.

콘솔로 만들고 아직 Terraform으로 가져오지 않은 리소스는 state에 없어서 `make down`이 지우지 못한다. `ManagedBy=console` 태그로 찾아 가져오거나 지운다([인프라 명세 13.2](05-infrastructure.md#132-콘솔-단계-규칙)).

```bash
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=ManagedBy,Values=console \
  --query "ResourceTagMappingList[].ResourceARN" --output table
```

**`make up`이 멈출 때**

- apply는 다시 실행해도 안전하다. 같은 명령으로 재실행하면 남은 부분만 만든다.
- 앱 인스턴스가 정상 판정을 못 받으면 `nat`가 켜져 있는지 먼저 본다(앱 서버는 부팅할 때 NAT를 거쳐 ECR·SSM에 접근한다).
- 마이그레이션이 실패하면 먼저 포트 포워딩 세션이 열렸는지(Session Manager 플러그인 설치 여부, 앱 인스턴스가 SSM에 연결됐는지) 보고, 다음으로 DB 사용자(`migrator`, `app_rw`)가 만들어졌는지 확인한다([인프라 명세 8.4](05-infrastructure.md#84-db-관리-작업-접속), [DB 스키마 5.1](03-db-schema.md#51-db-사용자-분리)).

**nightly-down 실패 메일을 받았을 때**

1. GitHub Actions 실행 기록에서 실패한 스택과 오류를 확인한다.
2. 위 확인 순서대로 원인을 고친 뒤 `nightly-down`을 수동 실행(`workflow_dispatch`)하거나 로컬에서 `make down`을 실행한다.
3. 그날 안에 고치지 못하면 최소한 시간당 과금이 큰 리소스(ALB, 앱 EC2, RDS, NAT)가 꺼졌는지 태그 검색으로 확인한다.
4. 다음 날 아침 Cost Explorer에서 밤사이 비용이 늘지 않았는지 확인한다.

## 6. 배포와 롤백

| 대상 | 배포 | 롤백 |
|---|---|---|
| 앱 | `app-deploy` 워크플로 | 이미지 태그를 이전 SHA로 바꾸고 인스턴스 새로고침 |
| 웹 | `web-deploy` 워크플로 | 이전 커밋으로 워크플로 재실행 |
| 인프라 | `infra-apply` 워크플로 | 이전 커밋으로 되돌리는 PR → apply |
| DB 스키마 | 앱 배포에 포함 | 되돌리지 않고 하위 호환으로 앞으로만 수정 |

상세는 [CI/CD](06-cicd.md).

## 7. 백업과 복구

| 대상 | 방식 | RPO | RTO |
|---|---|---|---|
| RDS (운영 단계, `rds_ephemeral = false`) | 자동 백업 7일 + 시점 복구, 월 1회 수동 스냅샷 | 5분 | 2시간 |
| RDS (개발 기간, `rds_ephemeral = true`) | 백업 없음. S3 `staging/`에서 replay로 공고 복구([DB 스키마 6.6](03-db-schema.md#66-재적재replay)), 채팅 기록은 보존하지 않음 | 마지막 수집일 | `make up` 약 20분 + replay |
| S3 데이터 버킷 | 버전 관리, 원본(`raw/`) 90일 보관 | 하루 | 재처리 1시간 |
| KB · S3 Vectors | `kb/` 문서로 전체 재동기화, 또는 `kb_synced_hash`를 비워 문서 재생성 | 하루 | 1시간 |
| 앱 | 상태 없음, 이미지는 ECR | 해당 없음 | 15분 (재배포) |
| 인프라 | Terraform 코드 + state 버킷 버전 관리 | 해당 없음 | 스택별 재적용. 온디맨드 스택 전체는 `make up` 약 20분 |
| 비밀정보 | Secrets Manager (삭제 시 복구 대기 기간) | 해당 없음 | 즉시 |

## 8. 데이터 보존과 개인정보

- 보존 기간과 삭제 방법은 [DB 스키마 10](03-db-schema.md#10-보존-정책)을 따른다.
- 원본 IP는 저장하지 않는다. 로그에도 세션 ID 해시 앞부분만 남긴다.
- 채팅 입력창에 "이름, 연락처 등 개인정보는 입력하지 마세요" 안내를 둔다.
- 개인정보 처리방침 페이지에 수집 항목(채팅 내용, IP 해시, 브라우저 정보), 목적, 보존 기간을 적는다.

## 9. 비용 관리

| 항목 | 방법 |
|---|---|
| 예산 | AWS Budgets 월 $100, 실제 50·80·100%와 예측 100% 알림. `bootstrap` 스택이라 온디맨드 스택을 꺼도 항상 동작한다 |
| 목표 | 개발 기간 월 $35 이하, 운영 단계 월 $100 이하(예상 약 $82~91). 단계별 예상은 [아키텍처 11.2](02-architecture.md#112-단계별-예상-비용) |
| 온디맨드 규칙 | 개발 기간에는 작업이 끝나면 `make down`. 다음 날 아침 Cost Explorer에서 어제 비용을 `Stack` 태그별로 보고, 온디맨드 스택 비용이 작업 시간만큼만 나왔는지 확인한다 |
| 안전장치 | 끄는 걸 잊어도 매일 03:00 KST에 `nightly-down`이 `make down`을 실행한다. 운영 단계에는 저장소 변수 `NIGHTLY_DOWN = off`로 멈춘다([인프라 명세 12.2](05-infrastructure.md#122-nightly-down)) |
| 추적 | 비용 할당 태그 `Project`, `Stack` 활성화, Cost Explorer에서 스택별 비용 확인 |
| 월간 검토 | 서비스별 상위 5개 항목, 전월 대비 변화, Bedrock 토큰 추이를 `docs/cost-log.md`에 기록 |
| 절감 수단 | [아키텍처 11.3](02-architecture.md#113-절감-수단) 표 참고 |

## 10. 정기 점검

| 주기 | 점검 |
|---|---|
| 매일 (운영 단계) | 수집 결과 메일·대시보드 확인, 알람 이력 |
| 매일 (개발 기간) | nightly-down 성공 여부, `collect_only` 수집 실패 메일 여부, 전날 비용(Cost Explorer) |
| 매주 | 품질 이슈 추이, `DOWN` 피드백 검토(평가셋 후보), 보안 회귀 스모크 결과, 드리프트 점검 결과, `Stack` 태그 기준 남은 온디맨드 리소스와 `ManagedBy=console` 태그(아직 가져오지 않은 콘솔 리소스) 확인([RB-08](#rb-08-make-updown-실패--꺼지지-않은-리소스)) |
| 매월 | 비용 검토, OS 패치(최신 AMI로 시작 템플릿 갱신 → 인스턴스 새로고침, NAT 포함), 의존성 업데이트, 관련성 수동 라벨링 |
| 분기 | DB 복구 리허설(GD-07), 장애 훈련 1회, 오리진 검증 비밀값 교체, 문서 갱신 |

## 11. 장애 보고서 양식

```markdown
# 장애 보고서: <제목>

- 날짜: YYYY-MM-DD
- 심각도: P1 / P2 / P3
- 작성자:

## 요약
무슨 일이 있었고, 사용자에게 어떤 영향이 있었는지 2~3문장.

## 타임라인 (KST)
| 시각 | 사건 |
|---|---|
| 10:02 | 알람 수신: ... |
| 10:05 | 원인 확인 시작 |
| 10:21 | 조치 완료 |

## 영향
- 기간: 19분
- 범위: 채팅 기능 (목록 조회는 정상)
- 영향 받은 요청 수:

## 원인
직접 원인과 근본 원인.

## 감지
어떻게 알았는가. 알람이 늦거나 없었다면 이유.

## 조치
무엇을 했는가.

## 재발 방지
| 항목 | 담당 | 기한 | 상태 |
|---|---|---|---|
```

## 12. 장애 훈련 보고서 양식

```markdown
# 장애 훈련 보고서: GD-XX <시나리오>

- 날짜·시간: YYYY-MM-DD HH:MM ~ HH:MM (KST)
- 대상 구성: 예) NAT 1단계(직접 구성)

## 가설
예) NAT 인스턴스가 종료되면 목록은 정상, 채팅은 DEGRADED로 응답하고 3분 안에 알람이 온다.

## 주입 방법
실행한 명령과 시각.

## 관찰 결과
| 지표 | 기대 | 실제 |
|---|---|---|
| 감지 시간 (주입 → 알람) | 3분 이내 | |
| 복구 시간 (주입 → 정상) | | |
| 사용자 오류 건수 | | |
| 목록 API 가용성 | 정상 | |

## 발견한 문제
예) ALB 헬스체크는 정상으로 판단해 장애가 대시보드에 바로 드러나지 않았다.

## 개선 조치
| 항목 | 결과 |
|---|---|

## 재훈련 결과 (개선 후)
이전 결과와 비교.
```
