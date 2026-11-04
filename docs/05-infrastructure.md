# 05. 인프라 명세 (네트워크 · 보안 · IAM · Terraform)

| 항목 | 내용 |
|---|---|
| 문서 버전 | v0.2 |
| 작성일 | 2026-11-02 |
| 변경 | 개발 기간 온디맨드 운영 반영 (2026-11-02) |
| 변경 | 기존 문제 수정: DB 관리 작업 접속, E2E·보안 회귀 워크플로, RAG 평가 방식 (2026-11-02) |
| 변경 | 수집 전용(`collect_only`) 모드 추가, Phase 2 RDS 상시 이유 명시 (2026-11-02) |
| 변경 | 콘솔 구축 후 Terraform으로 가져오는 방식(ADR-012), 일정 14주 (2026-11-02) |
| 변경 | 운영자 PC의 도구를 WSL에 둠 (2026-11-03) |
| 변경 | Phase 2 DB 접속용 임시 EC2 추가 (2026-11-03) |
| 변경 | API 키 시크릿 내용: 고용24 → 공공데이터포털 인증키(ADR-013) (2026-11-03) |
| 변경 | 8.3 S3 Vectors 인덱스의 필터 불가 키·인덱스 모드 추가 (2026-11-03) |
| 변경 | 10.4·13.3 Q-06 결과 반영: S3 Vectors·KB는 프로바이더가 지원 (2026-11-04) |
| 리전 | 서울 `ap-northeast-2` (가용영역 2a, 2c) + CloudFront 인증서용 `us-east-1` |
| 관련 문서 | [아키텍처](02-architecture.md), [ADR](10-adr.md) |

---

## 1. 이름·태그 규칙

- 리소스 이름: `fitjob-prod-<역할>` (예: `fitjob-prod-alb`, `fitjob-prod-app-asg`)
- 전역 고유 이름이 필요한 S3 버킷: `fitjob-prod-<용도>-<계정ID>`
- 모든 리소스 공통 태그(Terraform 프로바이더 `default_tags`로 일괄 적용):

| 태그 | 값 | 용도 |
|---|---|---|
| `Project` | `fitjob` | 비용 할당 태그(결제 콘솔에서 활성화) |
| `Env` | `prod` | |
| `ManagedBy` | `terraform`, `console` | 관리 주체 식별. 콘솔로 만들 때 `console`을 붙이고, Terraform으로 가져오면 `default_tags`가 `terraform`으로 바꾼다([13장](#13-콘솔-구축-후-terraform으로-가져오기)) |
| `Stack` | `bootstrap`, `network`, `storage`, `edge`, `pipeline`, `nat`, `database`, `app`, `observability` | 어느 Terraform 스택 소속인지. 꺼지지 않은 온디맨드 리소스를 찾을 때도 쓴다([운영 RB-08](08-operations.md#rb-08-make-updown-실패--꺼지지-않은-리소스)) |

## 2. 네트워크

### 2.1 VPC와 서브넷

| 이름 | CIDR | 가용영역 | 유형 | 배치 |
|---|---|---|---|---|
| VPC `fitjob-prod-vpc` | 10.0.0.0/16 | | | DNS 호스트 이름·확인 켬 |
| `public-2a` | 10.0.1.0/24 | 2a | 퍼블릭 | ALB 노드, NAT 인스턴스 |
| `public-2c` | 10.0.2.0/24 | 2c | 퍼블릭 | ALB 노드 |
| `app-2a` | 10.0.11.0/24 | 2a | 프라이빗 | EC2 앱 서버, VPC Lambda |
| `app-2c` | 10.0.12.0/24 | 2c | 프라이빗 | EC2 앱 서버, VPC Lambda |
| `db-2a` | 10.0.21.0/24 | 2a | 프라이빗(격리) | RDS 인스턴스 |
| `db-2c` | 10.0.22.0/24 | 2c | 프라이빗(격리) | DB 서브넷 그룹 요건, 복구 시 사용 |

나머지 대역(10.0.3.0 ~ 10.0.255.0)은 확장용으로 비워 둔다.

### 2.2 라우팅 테이블

| 라우팅 테이블 | 연결 서브넷 | 경로 |
|---|---|---|
| `rt-public` | public-2a, public-2c | `10.0.0.0/16 → local`, `0.0.0.0/0 → 인터넷 게이트웨이` |
| `rt-app` | app-2a, app-2c | `10.0.0.0/16 → local`, `0.0.0.0/0 → NAT 인스턴스 ENI`(`nat` 스택이 추가), S3 접두사 목록 → S3 게이트웨이 엔드포인트 |
| `rt-db` | db-2a, db-2c | `10.0.0.0/16 → local` (인터넷 경로 없음) |

- 라우팅 테이블 3개는 상시 `network` 스택에 있다. `rt-app`의 기본 경로(`0.0.0.0/0`)만 온디맨드 `nat` 스택이 별도 경로 리소스(`aws_route`)로 추가하고 지운다. `network` 스택의 라우팅 테이블은 인라인 `route` 블록 없이 정의한다. 인라인으로 쓰면 `network`를 apply할 때 `nat` 스택이 만든 경로를 지운다.
- **NAT가 꺼져 있으면 `rt-app`에 기본 경로가 없어 프라이빗 서브넷(앱 EC2, VPC Lambda)은 외부와 통신하지 않는다.** S3만 게이트웨이 엔드포인트로 닿는다. 그래서 `app` 스택은 `nat`가 켜진 뒤에 켠다(앱 서버가 부팅할 때 ECR·SSM에 접근).
- DB 서브넷은 외부로 나갈 일이 없으므로 NAT 경로를 넣지 않는다.
- `rt-app`의 기본 경로 대상은 인스턴스 ID가 아니라 **ENI**로 지정한다. fck-nat 전환 시 인스턴스가 바뀌어도 고정 ENI는 그대로라서 경로를 고칠 필요가 없다.

### 2.3 VPC 엔드포인트

| 엔드포인트 | 유형 | 비용 | 채택 |
|---|---|---|---|
| S3 | 게이트웨이 | 무료 | 채택. EC2·VPC Lambda의 S3 트래픽이 NAT를 거치지 않음 |
| Bedrock, Bedrock Runtime, ECR, SSM, Secrets Manager, CloudWatch Logs | 인터페이스 | 엔드포인트·가용영역마다 시간 요금 | **미채택**. 6종을 2개 가용영역에 두면 NAT 비용보다 커짐. NAT 의존을 줄여야 할 때 Bedrock Runtime부터 검토 |

### 2.4 NAT 인스턴스

온디맨드 `nat` 스택 소속이다. NAT 인스턴스, 퍼블릭 IP, NAT IAM 역할, `rt-app` 기본 경로가 함께 생기고 지워진다. 보안 그룹 `sg-nat`은 `network` 스택에 있다. Phase 2에는 DB 접속용 임시 EC2도 이 스택에 둔다([8.5](#85-db-접속용-임시-ec2-phase-2)).

| 항목 | 1단계: 직접 구성 | 2단계: fck-nat 고가용성 모드 |
|---|---|---|
| AMI | Amazon Linux 2023 (arm64) | fck-nat AMI (Amazon Linux 2023 기반, arm64) |
| 타입 | t4g.nano | t4g.nano |
| 배치 | public-2a, 퍼블릭 IP | public-2a, 1대짜리 Auto Scaling 그룹 |
| 소스/대상 확인 | 끔 (`source_dest_check = false`) | 모듈이 설정 |
| 경로 대상 | 인스턴스의 기본 ENI | 고정 내부 ENI(새 인스턴스에 자동 부착) |
| 장애 시 | 사람이 교체 | ASG가 새 인스턴스를 띄우고 ENI를 다시 붙임 |
| 관리 | Terraform `aws_instance` | Terraform 모듈 `RaJiska/fck-nat/aws` |

1단계 user data (Amazon Linux 2023):

```bash
#!/bin/bash
set -euxo pipefail

# iptables 서비스 설치 후 기본 규칙 로드
dnf install -y iptables-services
systemctl enable --now iptables

# IP 포워딩 (재부팅 후에도 유지)
echo "net.ipv4.ip_forward = 1" > /etc/sysctl.d/90-nat.conf
sysctl --system

# 기본 경로의 인터페이스 이름 자동 탐지 (t4g의 AL2023은 보통 eth0가 아니라 ens5)
IFACE=$(ip route show default | awk '{print $5; exit}')

# 기본 규칙의 FORWARD 거부 규칙 제거, VPC 대역 주소 변환
iptables -F FORWARD
iptables -t nat -A POSTROUTING -o "$IFACE" -s 10.0.0.0/16 -j MASQUERADE
iptables-save > /etc/sysconfig/iptables
```

- 22번 포트는 열지 않는다. 점검은 SSM Session Manager로 한다.
- 검증: 프라이빗 EC2에서 `curl -s https://checkip.amazonaws.com` 결과가 NAT 인스턴스의 퍼블릭 IP와 같아야 한다.

## 3. 보안 그룹

| 보안 그룹 | 인바운드 | 아웃바운드 |
|---|---|---|
| `sg-alb` | TCP 443 ← CloudFront 오리진용 관리형 접두사 목록 `com.amazonaws.global.cloudfront.origin-facing` | TCP 8000 → `sg-app` |
| `sg-app` | TCP 8000 ← `sg-alb` | TCP 443 → 0.0.0.0/0 (NAT 경유 AWS API·ECR), TCP 5432 → `sg-db` |
| `sg-lambda-vpc` | 없음 | TCP 443 → 0.0.0.0/0, TCP 5432 → `sg-db` |
| `sg-db` | TCP 5432 ← `sg-app`, `sg-lambda-vpc` | 없음 |
| `sg-nat` | 전체 ← 10.0.11.0/24, 10.0.12.0/24 | 전체 → 0.0.0.0/0 |

- **모든 보안 그룹은 상시 `network` 스택에 둔다.** 보안 그룹은 무료이고 서로 참조한다(`sg-db` ← `sg-app`, `sg-lambda-vpc`). 온디맨드 스택에 두면 destroy할 때 다른 스택의 규칙이 참조하고 있어 의존성 오류로 멈추고, 상시 `pipeline` 스택의 VPC Lambda가 쓰는 `sg-lambda-vpc`도 함께 사라질 수 있다.
- CloudFront 접두사 목록은 보안 그룹 규칙 수 할당량에 가중치로 계산된다. 적용 전 할당량을 확인한다.
- Phase 2의 DB 접속용 임시 EC2도 `sg-app`을 쓴다([8.5](#85-db-접속용-임시-ec2-phase-2)). `sg-db`를 바꾸지 않고 RDS에 닿기 위해서다.
- 어떤 보안 그룹도 22번 포트를 열지 않는다.

## 4. 엣지 보안 (CloudFront → ALB)

| 단계 | 설정 |
|---|---|
| 네트워크 | `sg-alb`가 CloudFront 접두사 목록만 허용 |
| 오리진 검증 헤더 | CloudFront 오리진 사용자 지정 헤더 `X-Origin-Verify: <비밀값>`. 비밀값은 Terraform `random_password`로 만들고 Secrets Manager에 보관 |
| ALB 리스너 443 | 규칙 1: 헤더 값 일치 → 대상 그룹 전달 / 기본 동작: 403 고정 응답 |
| TLS | ALB 보안 정책 `ELBSecurityPolicy-TLS13-1-2-2021-06` (TLS 1.2·1.3) |
| HTTP | CloudFront 뷰어 프로토콜 "HTTP를 HTTPS로 리다이렉트". ALB에는 80 리스너를 두지 않음 |

비밀값을 바꿀 때는 (1) ALB 규칙에 새 값을 추가, (2) CloudFront 헤더 교체, (3) 이전 값 규칙 삭제 순서로 해서 중단을 피한다.

### 4.1 CloudFront 동작

| 경로 | 오리진 | 캐시 정책 | 오리진 요청 정책 | 기타 |
|---|---|---|---|---|
| `/api/*` | ALB (`origin.<도메인>`, HTTPS만) | `CachingDisabled` | 사용자 지정: 뷰어 헤더(Host 제외), 쿼리 문자열 전체, `CloudFront-Viewer-Address` | 허용 메서드 전체 |
| 기본(`*`) | S3 웹 버킷 (OAC) | `CachingOptimized` | 없음 | 뷰어 요청 CloudFront Function으로 SPA 경로를 `/index.html`로 재작성 |

- SPA 대체 응답을 **배포 전체의 사용자 지정 오류 응답(403/404 → index.html)으로 만들지 않는다.** 그러면 API의 404까지 index.html로 바뀐다. 기본 동작에만 붙는 CloudFront Function으로 처리한다.
- 응답 헤더 정책: 관리형 `SecurityHeadersPolicy` (HSTS, `X-Content-Type-Options` 등)
- 가격 등급: 한국 엣지 로케이션이 포함되는 등급 선택

## 5. IAM

### 5.1 서비스 역할

| 역할 | 사용 주체 | 권한 (리소스는 특정 ARN으로 제한) |
|---|---|---|
| `fitjob-prod-app-ec2` | 앱 EC2 | `AmazonSSMManagedInstanceCore`, CloudWatch 에이전트 지표·로그 쓰기, ECR 이미지 받기(`fitjob-api` 리포지토리), `bedrock:InvokeModel`(사용 모델·추론 프로필), `bedrock:Retrieve`(KB), `secretsmanager:GetSecretValue`(`db-app`), `ssm:GetParameter`(`/fitjob/prod/*`) |
| `fitjob-prod-nat` | NAT 인스턴스 | `AmazonSSMManagedInstanceCore`. fck-nat 단계에서 ENI 부착 권한 추가 |
| `fitjob-prod-db-access` | DB 접속용 임시 EC2 (Phase 2) | `AmazonSSMManagedInstanceCore`만 ([8.5](#85-db-접속용-임시-ec2-phase-2)) |
| `fitjob-prod-lambda-collector` | 수집 Lambda | S3 `raw/*` 쓰기, `api-keys` 시크릿 읽기, 로그 |
| `fitjob-prod-lambda-normalizer` | 정규화 Lambda | S3 `raw/*` 읽기, `staging/*`·`quarantine/*` 쓰기, 로그 |
| `fitjob-prod-lambda-loader` | 적재 Lambda | S3 `staging/*` 읽기, `kb/*` 쓰기·삭제, `db-app` 시크릿 읽기, `ssm:GetParameter`(`/fitjob/prod/db/endpoint`), VPC ENI 관리, 로그 |
| `fitjob-prod-lambda-finalizer` | 마무리 Lambda | `db-app` 시크릿 읽기, `ssm:GetParameter`(`/fitjob/prod/db/endpoint`), VPC ENI 관리, 로그 |
| `fitjob-prod-sfn` | Step Functions | 위 Lambda 호출, `bedrock:StartIngestionJob`·`GetIngestionJob`(KB), SNS 발행(공용 토픽 `fitjob-prod-alerts`) |
| `fitjob-prod-scheduler` | EventBridge Scheduler | 상태 머신 실행 시작 |
| `fitjob-prod-kb` | Bedrock KB | S3 `kb/*` 읽기, S3 Vectors 인덱스 읽기·쓰기, 임베딩 모델 호출 |

역할은 쓰는 리소스와 같은 스택에 둔다. 앱 EC2 역할은 `app`, NAT 역할과 DB 접속용 임시 EC2 역할은 `nat`, Lambda·Step Functions·Scheduler 역할은 `pipeline`, KB 역할은 `storage`에 있다.

앱 EC2 역할은 DB 시크릿 중 `db-app`만 읽는다. 스키마를 바꾸는 `db-migrator`와 RDS 마스터 자격증명은 앱 서버에 주지 않는다. 앱 컨테이너는 인스턴스 역할을 그대로 쓰므로(IMDS 홉 제한 2), 여기에 권한을 주면 앱이 침해됐을 때 스키마 소유자 권한까지 샌다. 마이그레이션과 DB 사용자 생성은 배포 러너나 운영자 PC에서 한다([8.4](#84-db-관리-작업-접속)).

### 5.2 CI/CD 역할 (GitHub OIDC)

| 역할 | 신뢰 조건(`sub`) | 권한 |
|---|---|---|
| `fitjob-gha-app-deploy` | `repo:<owner>/fitjob:environment:prod` | ECR 푸시, SSM 파라미터 `image_tag` 쓰기, `autoscaling:StartInstanceRefresh`·조회, 마이그레이션용 SSM 포트 포워딩(`ssm:StartSession`을 문서 `AWS-StartPortForwardingSessionToRemoteHost`와 `Stack=app` 태그 인스턴스로 제한, `ec2:DescribeInstances`), `db-migrator` 시크릿과 `/fitjob/prod/db/endpoint` 읽기. 앱 사용자(`db-app`) 시크릿 읽기 없음 |
| `fitjob-gha-web-deploy` | `repo:<owner>/fitjob:environment:prod` | 웹 버킷 쓰기, CloudFront 무효화 |
| `fitjob-gha-tf-plan` | `repo:<owner>/fitjob:pull_request`, `repo:<owner>/fitjob:ref:refs/heads/main` | 읽기 전용 + state 버킷 읽기. PR의 `plan`, `drift-check`·`security-smoke` 예약 실행(main 브랜치)이 쓴다 |
| `fitjob-gha-tf-apply` | `repo:<owner>/fitjob:environment:prod` | 스택별 관리 권한 (GitHub 환경 승인 필요) |
| `fitjob-gha-eval` | `repo:<owner>/fitjob:ref:refs/heads/main`, `repo:<owner>/fitjob:pull_request` | `bedrock:InvokeModel`(사용 모델)만 — RAG 평가 프롬프트 모드 전용. 전체 모드는 공개 API만 써서 AWS 권한이 필요 없다([테스트 전략 5.3](07-test-plan.md#53-실행-방식)) |
| `fitjob-gha-env-down` | `repo:<owner>/fitjob:ref:refs/heads/main` (main 브랜치의 예약·수동 실행) | `nat`·`database`·`app`·`observability` 스택 destroy에 필요한 조회·삭제 권한, state 버킷의 온디맨드 스택 키 읽기·쓰기, 상시 스택 state 읽기. 생성·변경 권한 없음 — nightly-down 전용([12.2](#122-nightly-down)) |

- 장기 액세스 키는 만들지 않는다. 신뢰 정책 예시는 [CI/CD](06-cicd.md#5-aws-인증-github-oidc) 참고.
- OIDC 토큰의 `sub`에는 이벤트 종류(예약 실행, 수동 실행)가 담기지 않는다. `fitjob-gha-env-down`은 `nightly-down` 워크플로에서만 쓰고, 더 좁혀야 하면 전용 GitHub 환경을 만들어 `environment` 조건으로 바꾼다.
- `bootstrap` 스택은 이 역할들을 만드는 스택이라 CI에서 apply하지 않고 로컬에서만 apply한다.
- 개인 작업용 IAM 사용자는 MFA 필수, 루트 계정은 MFA만 설정하고 사용하지 않는다.

## 6. 비밀정보와 설정

| 이름 | 저장소 | 내용 | 스택 |
|---|---|---|---|
| RDS 마스터 자격증명 | Secrets Manager (RDS 관리) | `manage_master_user_password = true` | database |
| `fitjob/prod/db-migrator` | Secrets Manager | 마이그레이션 사용자 | storage |
| `fitjob/prod/db-app` | Secrets Manager | 앱 사용자 `app_rw` | storage |
| `fitjob/prod/api-keys` | Secrets Manager | 사람인 API 키, 공공데이터포털 인증키 | storage |
| `fitjob/prod/origin-verify` | Secrets Manager | CloudFront 오리진 검증 값 | storage |
| `/fitjob/prod/app/image_tag` | SSM Parameter Store | 배포할 이미지 태그(git SHA) | storage |
| `/fitjob/prod/app/chat_daily_limit` | SSM Parameter Store | 일일 채팅 상한 | storage |
| `/fitjob/prod/app/reasons_mode` | SSM Parameter Store | 매칭 이유 생성 방식. `llm`(기본) 또는 `template`. Bedrock 쓰로틀링 때 `template`로 전환([운영 RB-07](08-operations.md#rb-07-bedrock-쓰로틀링--오류)) | storage |
| `/fitjob/prod/app/ip_hash_salt` | SSM Parameter Store (SecureString) | IP 해시 솔트 | storage |
| `/fitjob/prod/cwagent` | SSM Parameter Store | CloudWatch 에이전트 설정 | storage |
| `/fitjob/prod/db/endpoint` | SSM Parameter Store | RDS 접속 주소. 앱·적재·마무리 Lambda가 실행 시 읽는다 | database |

Secrets Manager 시크릿은 모두 5개다.

- **시크릿은 상시 `storage` 스택에 둔다.** 시크릿을 지우면 복구 대기 기간(7~30일) 동안 같은 이름으로 다시 만들 수 없어서, 온디맨드 스택에 두면 다시 켤 때 apply가 실패한다. 예외인 RDS 마스터 자격증명은 RDS가 만들고 지우는 시크릿이라 `database` 스택을 따라가고, 이름이 매번 달라 이 문제가 없다.
- **앱 설정 SSM 파라미터도 `storage`에 둔다.** `app` 스택이 꺼져 있어도 배포 파이프라인이 `image_tag`를 갱신해야 하기 때문이다. `image_tag` 값은 파이프라인이 바꾸므로 Terraform은 값 변경을 무시한다(`ignore_changes`).
- **DB 주소는 `database` 스택이 기록한다.** 상시 `pipeline` 스택이 온디맨드 `database` 스택을 Terraform으로 참조하지 않도록, 앱과 Lambda는 실행할 때 이 파라미터를 읽는다.

Terraform state에 비밀값이 남지 않도록, 사람이 넣는 값(API 키)은 Terraform이 빈 시크릿만 만들고 값은 콘솔이나 CLI로 넣는다.

## 7. 컴퓨팅

### 7.1 앱 서버 시작 템플릿

| 항목 | 값 |
|---|---|
| AMI | Amazon Linux 2023 (SSM 공개 파라미터로 최신 조회). 아키텍처는 인스턴스 타입에 맞춘다(t3는 x86_64, t4g는 arm64) |
| 타입 | 변수 `app_instance_type`, 기본 t3.micro (크레딧 모드 `standard`로 예상 밖 과금 방지, 부하 테스트 후 재검토). t4g로 바꾸려면 arm64 이미지가 필요하다 |
| 디스크 | gp3 16GB, 암호화 |
| IMDS | v2 필수, 홉 제한 2 (컨테이너가 인스턴스 역할을 쓰려면 2 필요) |
| 퍼블릭 IP | 없음 |
| 보안 그룹 | `sg-app` |

user data 요지:

```bash
#!/bin/bash
set -euxo pipefail
REGION=ap-northeast-2
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

dnf install -y docker amazon-cloudwatch-agent
systemctl enable --now docker

TAG=$(aws ssm get-parameter --region "$REGION" --name /fitjob/prod/app/image_tag --query Parameter.Value --output text)
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

docker run -d --name api --restart unless-stopped -p 8000:8000 \
  --log-driver awslogs \
  --log-opt awslogs-region="$REGION" \
  --log-opt awslogs-group=/fitjob/prod/api \
  -e APP_ENV=prod \
  "${REGISTRY}/fitjob-api:${TAG}"

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -s -c ssm:/fitjob/prod/cwagent
```

부팅마다 패키지를 설치하면 1~2분이 걸린다. 운영이 안정되면 Packer로 Docker·에이전트가 들어간 AMI를 미리 만드는 것을 검토한다(P2).

### 7.2 Auto Scaling 그룹

| 항목 | 값 |
|---|---|
| 서브넷 | app-2a, app-2c |
| 용량 | 변수 `asg_min` / `asg_desired` / `asg_max` (아래 표) |
| 헬스체크 | ELB, 유예 180초 |
| 그룹 지표 | 수집 활성화 (`GroupInServiceInstances` 등, 확장 한계 알람에 필요) |
| 스케일링 | 대상 추적: 평균 CPU 50% (1차). 부하 테스트 후 `ALBRequestCountPerTarget` 전환 검토 |
| 인스턴스 새로고침 | 최소 정상 100%, 최대 정상 200%, 워밍업 180초. 새 인스턴스를 먼저 띄워 정상 판정을 받은 뒤 기존 인스턴스를 내리므로 1대 구성에서도 무중단이다. 실패 시 배포 파이프라인이 이전 태그로 되돌림([CI/CD 6.2](06-cicd.md#62-롤백을-직접-구현하는-이유)) |

| 변수 | 기본값(운영·개발) | 부하 테스트·장애 훈련 기간 | 비고 |
|---|---|---|---|
| `asg_min` / `asg_desired` / `asg_max` | 1 / 1 / 4 | 2 / 2 / 4 | 2대일 때 가용영역 2곳에 1대씩 분산. 훈련이 끝나면 기본값으로 되돌린다 |
| `app_instance_type` | t3.micro | t3.micro | t4g 전환 시 월 약 $2(1대 기준) 절감, arm64 이미지 필요 |

### 7.3 ALB

| 항목 | 값 |
|---|---|
| 서브넷 | public-2a, public-2c |
| 리스너 | 443만 (ACM 서울 인증서) |
| 대상 그룹 | HTTP 8000, 헬스체크 `/api/health`, 간격 15초, 정상 2회·비정상 3회 |
| 등록 취소 지연 | 30초 |
| 유휴 시간 제한 | 60초 |
| 액세스 로그 | S3 로그 버킷 (P1) |
| DNS | `origin.<도메인>` 별칭 레코드를 `app` 스택이 ALB와 함께 만들고 지운다(ALB DNS 이름이 다시 만들 때마다 바뀌기 때문) |

## 8. 데이터

### 8.1 RDS PostgreSQL

| 항목 | 값 |
|---|---|
| 스택 | `database` (온디맨드). RDS, DB 서브넷 그룹, 파라미터 그룹, DB 주소 SSM 파라미터 |
| 인스턴스 | db.t4g.micro, Single-AZ, 2a |
| 스토리지 | gp3 20GB, 자동 확장 최대 50GB, KMS 암호화 |
| 서브넷 그룹 | db-2a, db-2c |
| 접근 | 퍼블릭 접근 끔, `sg-db` |
| 백업 | 자동 백업 7일(시점 복구) |
| 삭제 보호 | 변수 `rds_ephemeral`로 정한다(아래 표) |
| 파라미터 그룹 | `rds.force_ssl = 1`, `log_min_duration_statement = 500` |
| 유지 관리 창 | 월요일 04:00~04:30 KST (수집 05:00 전) |
| 백업 창 | 03:00~03:30 KST |

| `rds_ephemeral` | `deletion_protection` | `skip_final_snapshot` | 쓰는 때 |
|---|---|---|---|
| `false` (기본) | `true` | `false` (삭제 시 최종 스냅샷) | Phase 2(데이터 파이프라인, W5~6) 동안, 운영 단계(반드시). `make down`이 `database` 스택을 건너뛴다 |
| `true` | `false` | `true` | Phase 3~5(W7~11)에 RDS도 `make up`·`make down`에 포함할 때. 공고는 S3 `staging/`에서 replay로 다시 채운다([DB 스키마 6.6](03-db-schema.md#66-재적재replay)) |

**Phase 2 동안 RDS를 켜두는 이유:** 이 단계에서 만드는 적재 로직 중에는 여러 날의 DB 상태가 이어져야 확인할 수 있는 것이 많다.

| 로직 | 이전 날짜의 DB 상태가 필요한 이유 |
|---|---|
| 마감 처리 | "어제 있던 공고가 오늘 응답에 없으면 `CLOSED`"는 어제 적재 결과와 비교한다([DB 스키마 6.4](03-db-schema.md#64-마감-처리)) |
| 수집 건수 급감 판정 | 최근 7일 `ingestion_source_stats` 평균과 비교한다([테스트 전략 3.2](07-test-plan.md#32-배치-단위)) |
| 중복 병합·대표 승격 | 먼저 들어온 공고의 `first_seen_at`, 대표 공고가 마감될 때의 승격을 날짜를 넘겨 확인한다([DB 스키마 6.3](03-db-schema.md#63-중복-판정)) |
| 마이그레이션 | 데이터가 있는 상태에서 스키마를 바꿔 봐야 실제 배포와 같은 조건이 된다 |

RDS를 지우면 그때마다 지난 날짜들을 순서대로 replay해서 상태를 다시 만들어야 해서, 파이프라인을 자주 고치는 이 단계에서는 번거롭다. 데이터 유실이 걱정돼서가 아니다(공고는 S3에서 복구된다). 파이프라인이 안정된 Phase 3부터는 `true`로 바꿔도 된다.

- `rds_ephemeral`을 `true`로 바꾼 뒤에는 먼저 apply해서 삭제 보호를 끈 다음에야 destroy할 수 있다.
- `true`일 때는 RDS를 지우면 자동 백업도 함께 사라진다. 채팅 기록 등 개발 중 데이터는 보존하지 않는다.

RDS를 NAT와 같은 2a에 두는 이유는 [아키텍처 10. 장애 영향 분석](02-architecture.md#10-장애-영향-분석) 참고.

### 8.2 S3 버킷

| 버킷 | 용도 | 설정 |
|---|---|---|
| `fitjob-prod-data-<계정ID>` | 수집 데이터, KB 문서 | 퍼블릭 차단, SSE-S3, 버전 관리(이전 버전 7일), 수명 주기([DB 스키마 8](03-db-schema.md#8-s3-데이터-버킷-구조)) |
| `fitjob-prod-web-<계정ID>` | 웹 정적 파일 | 퍼블릭 차단, CloudFront OAC만 허용하는 버킷 정책 |
| `fitjob-prod-logs-<계정ID>` | ALB 액세스 로그 | 30일 후 삭제 |
| `fitjob-tfstate-<계정ID>` | Terraform state | 퍼블릭 차단, 버전 관리, 암호화 |

state 버킷은 `bootstrap`, 나머지 버킷은 `storage` 스택에 있다(모두 상시). S3 Vectors 벡터 버킷, KB(8.3), ECR도 `storage`에 있다.

### 8.3 Bedrock

| 항목 | 값 |
|---|---|
| KB 데이터 소스 | S3 `fitjob-prod-data-<계정ID>/kb/postings/` |
| 분할 전략 | 분할 없음 (문서 1개 = 청크 1개) |
| 임베딩 모델 | Titan Text Embeddings V2, 1024차원 (서울 리전 지원 확인 필요) |
| 벡터 저장소 | S3 Vectors 벡터 버킷 `fitjob-prod-vectors`, 인덱스 `postings`, 코사인 거리. 필터 불가(non-filterable) 메타데이터 키로 `AMAZON_BEDROCK_TEXT`, `AMAZON_BEDROCK_METADATA`를 지정한다. **인덱스를 만들 때만 정할 수 있고 나중에 바꿀 수 없다**(이름·차원·거리도 같음). 2026-09-30 이후 만든 버킷이라 인덱스 모드는 `ENHANCED`(필터를 먼저 적용) |
| LLM | Claude Haiku 5.5 (서울에서 호출 방식 확인 필요) |
| 모델 접근 | Bedrock 콘솔에서 사용할 모델 접근 활성화 |

### 8.4 DB 관리 작업 접속

RDS는 프라이빗 DB 서브넷에 있어 밖에서 직접 닿지 않는다. 마이그레이션과 DB 사용자 생성은 **앱 인스턴스를 거치는 SSM 포트 포워딩**으로 접속해서 한다. 앱 인스턴스가 아직 없는 Phase 2에는 [8.5](#85-db-접속용-임시-ec2-phase-2)의 임시 EC2를 거친다. 앱 서버 자체에는 이 작업에 필요한 자격증명을 주지 않는다([5.1](#51-서비스-역할)).

| 작업 | 언제 | 실행 위치 | 자격증명 |
|---|---|---|---|
| `alembic upgrade head` | 앱 배포 | GitHub Actions 러너 (`app-deploy`) | `fitjob/prod/db-migrator` (배포 역할이 읽음) |
| `alembic upgrade head` | `make up` | 운영자 PC | `fitjob/prod/db-migrator` (운영자 IAM 사용자) |
| `migrator`·`app_rw` 사용자 생성 | `make up`에서 RDS를 새로 만든 경우 | 운영자 PC | RDS 마스터 자격증명 |

절차:

1. `Stack=app` 태그가 붙은 실행 중인 앱 인스턴스 1대를 고른다. Phase 2에는 `Name=fitjob-prod-db-access` 인스턴스를 고른다([8.5](#85-db-접속용-임시-ec2-phase-2)).
2. 포트 포워딩 세션을 연다.
   ```bash
   aws ssm start-session --target "$INSTANCE_ID" \
     --document-name AWS-StartPortForwardingSessionToRemoteHost \
     --parameters "host=$DB_ENDPOINT,portNumber=5432,localPortNumber=15432"
   ```
3. 로컬 `15432` 포트로 접속해 작업한다. 마이그레이션은 배포할 이미지로 `docker run --network host ... alembic upgrade head`를 실행한다.
4. 끝나면 세션을 닫는다.

- `rds.force_ssl = 1`이라 TLS가 필요하다. 접속 문자열에 `host=<RDS 주소> hostaddr=127.0.0.1 port=15432 sslmode=verify-full`을 함께 주면, 터널로 접속하면서도 인증서 이름 검증을 유지한다.
- 앱 인스턴스의 `sg-app`은 이미 `sg-db`로 5432 아웃바운드가 열려 있어 보안 그룹을 바꿀 필요가 없다.
- 필요 도구: AWS CLI, Session Manager 플러그인, Docker. 러너는 `run-migration.sh`가 플러그인을 설치한다. 운영자 PC는 WSL(Ubuntu)에 설치하고 거기서 실행한다(Windows에는 두지 않는다).
- 운영자 PC에서 처음 마이그레이션할 때, WSL에서 띄운 `docker run --network host` 컨테이너가 WSL의 `15432` 포트에 닿는지 확인한다. Docker는 Docker Desktop의 WSL 연동이라 설정에 따라 네트워크가 다를 수 있다.
- 앱 인스턴스가 없으면(`app` 스택이 꺼짐) 접속할 수 없다. 그래서 배포는 이때 마이그레이션을 건너뛰고, `make up`은 `app`을 켠 다음에 이 단계를 실행한다.

### 8.5 DB 접속용 임시 EC2 (Phase 2)

Phase 2(W5~6)에는 `app` 스택이 아직 없어서 8.4의 경유지인 앱 인스턴스가 없다. 그런데 이 단계에서 DB 사용자 생성, 첫 마이그레이션, 적재 결과 확인을 해야 한다. 그래서 Phase 3에 앱 서버가 생길 때까지 포트 포워딩 경유지로만 쓰는 작은 EC2를 둔다.

| 항목 | 값 |
|---|---|
| 이름 | `fitjob-prod-db-access` |
| 스택 | `nat` (온디맨드). SSM 연결에 NAT가 필요하고, 켜고 끄는 시점이 NAT와 같아서다. `make down`·nightly-down이 NAT와 함께 지운다 |
| AMI·타입 | Amazon Linux 2023(arm64, SSM 에이전트 포함), t4g.nano |
| 배치 | `app-2a`, 퍼블릭 IP 없음 |
| 보안 그룹 | `sg-app`. 새로 만들지 않는다. `sg-db`가 이미 `sg-app`의 5432 접속을 허용하고, `sg-app`의 443 아웃바운드로 NAT를 거쳐 SSM에 연결된다 |
| IAM 역할 | `fitjob-prod-db-access`: `AmazonSSMManagedInstanceCore`만. 시크릿·DB 권한은 주지 않는다 |
| 디스크·IMDS | 루트 디스크 암호화, IMDSv2 필수 |
| 비용 | NAT 인스턴스와 같은 사양이라 24시간 켜도 월 약 $4. 작업할 때만 켜므로 Phase 2 동안 $1 미만 |

- 이 EC2에서는 아무것도 실행하지 않는다. 운영자 PC가 이 EC2를 거쳐 RDS에 닿기만 하고, 자격증명은 운영자 PC가 Secrets Manager에서 읽는다.
- 쓰는 법은 8.4 절차와 같다. 1단계에서 앱 인스턴스 대신 `Name=fitjob-prod-db-access` 인스턴스를 고른다.
- Phase 3에서 `app` 스택을 가져온 뒤 앱 인스턴스로 접속되는 것을 확인하면 `nat` 스택 코드에서 지운다([로드맵 Phase 3](09-roadmap.md#phase-3-api웹-w79)).

## 9. 관측·알림

| 리소스 | 설정 | 스택 |
|---|---|---|
| SNS 토픽 `fitjob-prod-alerts`(서울) | 이메일 구독. 비용 알림, 수집 실패 알림, CloudWatch 알람이 함께 쓰는 공용 토픽 | bootstrap (상시) |
| AWS Budgets | 월 $100, 실제 50/80/100%·예측 100% 알림 → `fitjob-prod-alerts` | bootstrap (상시) |
| 로그 그룹 | `/fitjob/prod/api`(storage), `/aws/lambda/fitjob-prod-*`·`/aws/vendedlogs/states/fitjob-prod-ingest`(pipeline) — 보존 30일. 상시 스택에 둬서 온디맨드 스택을 꺼도 로그가 남는다 | storage, pipeline (상시) |
| 대시보드, 알람 | [운영 문서 2·4장](08-operations.md#4-알람) | observability (운영 단계에만) |
| Route 53 헬스체크 | `https://app.<도메인>/api/health/deep`, 30초 간격 | observability (운영 단계에만) |
| SNS 토픽 `fitjob-prod-alerts-use1`(us-east-1) | Route 53 헬스체크 알람용(헬스체크 지표가 us-east-1에만 있음) → 같은 이메일 | observability (운영 단계에만) |

- Budgets와 공용 SNS 토픽을 `bootstrap`에 두는 이유: `observability`에 두면 그 스택을 끌 때 비용 알림까지 사라진다. 상시 `pipeline` 스택의 수집 실패 알림도 같은 토픽을 쓰므로, 꺼지는 스택에 기대지 않는다.
- 개발 기간에는 `observability`를 켜지 않으므로 대시보드·알람이 없다. 비용 알림(Budgets)과 수집 실패 알림만 동작한다.

알람 목록과 임계값은 [운영 문서](08-operations.md#4-알람) 참고.

## 10. Terraform 구조

### 10.1 저장소 배치

```
infra/
├── Makefile              # up, down, up-app, down-app (12장)
├── modules/
│   ├── network/          # VPC, 서브넷, 라우팅 테이블, IGW, S3 엔드포인트, 보안 그룹
│   ├── nat-instance/     # 1단계 직접 구성 NAT
│   ├── alb/
│   ├── app-asg/          # 시작 템플릿, ASG, 스케일링 정책
│   ├── rds/
│   ├── edge/             # CloudFront, OAC, CloudFront Function
│   ├── knowledge-base/   # KB, S3 Vectors, KB 역할
│   ├── ingest-pipeline/  # Lambda, Step Functions, Scheduler
│   └── observability/    # 대시보드, 알람, 헬스체크
└── stacks/
    ├── bootstrap/        # [상시] state 버킷, GitHub OIDC 공급자·역할, AWS Budgets, 공용 SNS 토픽
    ├── network/          # [상시] VPC, 서브넷 6개, 라우팅 테이블 3개, IGW, S3 게이트웨이 엔드포인트, 보안 그룹 전부
    ├── storage/          # [상시] S3 데이터·웹·로그 버킷, S3 Vectors, KB, ECR, Secrets Manager, 앱 SSM 파라미터, API 로그 그룹
    ├── edge/             # [상시] CloudFront, ACM(서울·us-east-1), Route 53 호스팅 영역
    ├── pipeline/         # [상시] Lambda, Step Functions, EventBridge Scheduler (Lambda 코드 패키징 포함)
    ├── nat/              # [온디맨드] NAT 인스턴스, rt-app 기본 경로, (Phase 2) DB 접속용 임시 EC2
    ├── database/         # [온디맨드] RDS, DB 서브넷 그룹, 파라미터 그룹, DB 주소 SSM 파라미터
    ├── app/              # [온디맨드] ALB, 시작 템플릿, ASG, 앱 IAM, origin.<도메인> 레코드
    └── observability/    # [온디맨드] 대시보드, 알람, Route 53 헬스체크, us-east-1 SNS 토픽
```

`bootstrap`은 state 버킷을 담는 스택이라, 콘솔로 만든 state 버킷을 처음에는 로컬 state로 import한 뒤 백엔드를 S3로 옮긴다(`terraform init -migrate-state`).

### 10.2 스택 구성과 적용 순서

스택은 상시 5개, 온디맨드 4개, 모두 9개다. 개발 기간에 온디맨드 스택만 켜고 끄는 이유는 [ADR-011](10-adr.md#adr-011-개발-기간에는-비싼-리소스를-온디맨드로-운영한다) 참고.

| 스택 | 구분 | 담는 것 | 이렇게 둔 이유 |
|---|---|---|---|
| `bootstrap` | 상시 | state 버킷, GitHub OIDC 공급자·역할, AWS Budgets(월 $100), 공용 SNS 토픽 `fitjob-prod-alerts` | Budgets를 `observability`에 두면 끌 때 비용 알림까지 사라진다 |
| `network` | 상시 | VPC, 서브넷 6개, 라우팅 테이블 3개, IGW, S3 게이트웨이 엔드포인트, 보안 그룹 전부 | 무료. 보안 그룹은 스택끼리 서로 참조해서 온디맨드 스택에 두면 destroy 때 의존성 오류가 난다 |
| `storage` | 상시 | S3 데이터·웹·로그 버킷, S3 Vectors, KB, ECR, Secrets Manager, 앱 SSM 파라미터, API 로그 그룹 | 저장 비용만 든다. 시크릿은 삭제 후 복구 대기 기간 동안 같은 이름으로 다시 만들 수 없다 |
| `edge` | 상시 | CloudFront, ACM 인증서(서울, us-east-1), Route 53 호스팅 영역 | CloudFront는 다시 만드는 데 수 분이 걸리고, 인증서는 DNS 검증을 다시 해야 하며, 호스팅 영역을 다시 만들면 네임서버가 바뀐다 |
| `pipeline` | 상시 | Lambda, Step Functions, EventBridge Scheduler | 실행할 때만 과금. 매일 05:00 예약 실행의 모드는 변수 `schedule_mode`로 정한다(개발 중 `collect_only`: NAT·RDS 없이 S3까지만, 운영 `full`) |
| `nat` | 온디맨드 | NAT 인스턴스, `rt-app`의 `0.0.0.0/0` 경로. Phase 2에는 DB 접속용 임시 EC2 | 시간당 과금(인스턴스, 퍼블릭 IPv4). 라우팅 테이블 자체는 `network`에 있다. 임시 EC2는 SSM 연결에 NAT가 필요해 함께 켜고 끈다([8.5](#85-db-접속용-임시-ec2-phase-2)) |
| `database` | 온디맨드 | RDS, DB 서브넷 그룹, 파라미터 그룹, DB 주소 SSM 파라미터 | 시간당 과금. 처음에는 계속 켜두고, 익숙해지면 up/down에 포함한다([8.1](#81-rds-postgresql)) |
| `app` | 온디맨드 | ALB, 시작 템플릿, Auto Scaling 그룹, 앱 IAM 역할, `origin.<도메인>` Route 53 레코드 | 시간당 과금. ALB DNS 이름이 다시 만들 때마다 바뀌므로 `origin` 레코드를 함께 생성·삭제한다 |
| `observability` | 온디맨드 | 대시보드, 알람, Route 53 헬스체크, us-east-1 SNS 토픽 | 운영 단계에서만 켠다 |

스택을 나눈 이유:

| 이유 | 설명 |
|---|---|
| 영향 범위 축소 | 앱 변경 `plan`이 RDS를 건드리지 않는다 |
| 비용 절감 | 개발 기간에 온디맨드 스택만 켜고 끈다. 상시 스택만 남은 대기 비용은 월 약 $5 |
| 속도 | 스택별 plan이 빠르다 |

스택 간 값(서브넷 ID, 보안 그룹 ID 등)은 `terraform_remote_state`로 읽는다. **상시 스택은 온디맨드 스택을 참조하지 않는다.** 온디맨드 스택이 만든 값 중 다른 곳에서 필요한 것(DB 주소)은 SSM 파라미터로 넘기고 실행할 때 읽는다.

| 스택 | 구분 | Terraform 참조 | 실행할 때 켜져 있어야 하는 스택 | 적용 순서 |
|---|---|---|---|---|
| `bootstrap` | 상시 | 없음 | | 0 |
| `network` | 상시 | bootstrap | | 1 |
| `storage` | 상시 | bootstrap | | 2 |
| `edge` | 상시 | storage (웹 버킷, 오리진 검증 시크릿) | | 3 |
| `pipeline` | 상시 | bootstrap (SNS), network, storage | 수집을 실행할 때 `nat`, `database` | 4 |
| `nat` | 온디맨드 | network | | 5 |
| `database` | 온디맨드 | network | | 6 |
| `app` | 온디맨드 | network, storage, edge (서울 인증서, 호스팅 영역) | `nat`(부팅 시 ECR·SSM 접근), `database` | 7 |
| `observability` | 온디맨드 | bootstrap, edge, nat, database, app | | 8 |

- 상시: `bootstrap` → `network` → `storage` → `edge` → `pipeline`
- 온디맨드 켜기: `nat` → `database` → `app` → (운영 단계면) `observability`
- 끄기: 켠 순서의 역순 (`observability` → `app` → `database` → `nat`)

### 10.3 기본 설정

```hcl
terraform {
  required_version = ">= 1.11"   # S3 자체 잠금(use_lockfile) 정식 지원 버전 이상
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }  # 구현 시 최신 메이저 확인
  }
  backend "s3" {
    bucket       = "fitjob-tfstate-<계정ID>"
    key          = "stacks/network/terraform.tfstate"
    region       = "ap-northeast-2"
    encrypt      = true
    use_lockfile = true   # S3 자체 잠금, DynamoDB 잠금 테이블 불필요
  }
}

provider "aws" {
  region = "ap-northeast-2"
  default_tags { tags = { Project = "fitjob", Env = "prod", ManagedBy = "terraform", Stack = "network" } }
}

provider "aws" {
  alias  = "us_east_1"   # edge 스택의 CloudFront 인증서용
  region = "us-east-1"
}
```

### 10.4 코드 품질

- 커밋 전: `terraform fmt`, `terraform validate`, `tflint` (pre-commit 훅)
- PR: 위 항목 + `checkov` 정적 분석, 스택별 `plan` 결과를 PR 댓글로
- 매일: `plan -detailed-exitcode`로 드리프트 점검, 변경이 있으면 알림. 대상은 상시 스택 전부와 켜져 있는(state에 리소스가 있는) 온디맨드 스택이다. 꺼진 온디맨드 스택은 plan이 "전부 생성"으로 나오므로 점검하지 않는다. 개발 기간에는 03:00 nightly-down 뒤에 돌기 때문에 사실상 상시 스택만 점검한다
- Terraform 프로바이더가 아직 지원하지 않는 리소스가 있으면 해당 부분만 AWS CLI 스크립트로 보완하고 이 문서에 기록한다. S3 Vectors 벡터 버킷·인덱스와 KB(S3 Vectors 저장소)는 프로바이더 6.71.0이 지원한다([요구사항 Q-06](01-requirements.md#9-미결-사항-구현-전-확인)).

## 11. 보안 체크리스트

| 항목 | 확인 |
|---|---|
| 루트 계정 MFA, 액세스 키 없음 | ☐ |
| 작업용 IAM 사용자 MFA | ☐ |
| 22번 포트 미개방 (모든 SG) | ☐ |
| 앱·DB 퍼블릭 IP 없음 | ☐ |
| ALB는 CloudFront 접두사 목록 + 오리진 헤더로만 접근 | ☐ |
| S3 퍼블릭 접근 차단 (계정 수준) | ☐ |
| RDS·EBS·S3 암호화 | ☐ |
| IMDSv2 필수 | ☐ |
| 시크릿이 코드·이미지·state에 평문으로 없음 | ☐ |
| CI는 OIDC, 장기 키 없음 | ☐ |
| ECR 이미지 스캔, 심각(CRITICAL) 취약점 0 | ☐ |
| checkov 고위험 항목 0 (예외는 사유 기록) | ☐ |
| CloudTrail 관리 이벤트 활성(기본 90일 이벤트 기록 확인) | ☐ |

## 12. 온디맨드 운영

개발 기간에는 시간당 과금되는 온디맨드 스택(`nat`, `database`, `app`, `observability`)을 작업할 때만 켠다. 결정 배경은 [ADR-011](10-adr.md#adr-011-개발-기간에는-비싼-리소스를-온디맨드로-운영한다), 비용은 [아키텍처 11](02-architecture.md#11-비용-추정-서울-리전-월) 참고.

### 12.1 Makefile 타깃

| 타깃 | 하는 일 | 소요 시간 |
|---|---|---|
| `make up` | `nat` → `database` → `app` 순서로 apply, 마지막에 DB 준비 단계 실행 | 약 15~20분 |
| `make down` | 켜진 온디맨드 스택을 역순(`observability` → `app` → `database` → `nat`)으로 destroy. `rds_ephemeral = false`면 `database`는 건너뛴다 | 약 10분 |
| `make up-app` | RDS는 그대로 두고 `nat` → `app`만 apply, 마이그레이션 실행 | `make up`보다 RDS 생성 시간만큼 짧다 |
| `make down-app` | RDS는 그대로 두고 `app` → `nat`만 destroy | `make down`과 비슷 |

`make up`의 마지막 단계(DB 준비):

1. DB 사용자 준비: RDS를 새로 만들었으면 운영자 PC에서 SSM 포트 포워딩으로 접속해([8.4](#84-db-관리-작업-접속)) 마스터 자격증명으로 `migrator`·`app_rw` 사용자를 만든다(이미 있으면 건너뜀, [DB 스키마 5.1](03-db-schema.md#51-db-사용자-분리)).
2. 같은 포트 포워딩으로 `image_tag`의 이미지를 써서 `alembic upgrade head`를 실행한다. `app` 스택이 꺼져 있는 동안 배포가 마이그레이션을 건너뛰었어도 여기서 따라잡는다.
3. DB가 비어 있으면(`job_postings` 0건) `staging/`의 가장 최근 날짜로 replay를 시작한다(`{"mode": "replay", "run_date": "YYYY-MM-DD"}`, [DB 스키마 6.6](03-db-schema.md#66-재적재replay)). replay는 Step Functions에서 비동기로 돌므로 `make up` 소요 시간에 넣지 않는다. 목록은 적재가 끝나면(수 분), 채팅은 KB 동기화가 끝나면 정상 동작한다.
4. `/api/health/deep`으로 확인하고, 보안 회귀 스모크 스크립트(`scripts/security-smoke.sh`)를 실행한다([테스트 전략 8](07-test-plan.md#8-인프라보안-회귀-테스트)).

`observability`는 `make up`에 넣지 않는다. 운영 단계로 전환할 때 해당 스택에서 직접 apply한다. `make down`은 `observability`가 켜져 있으면 먼저 지운다.

### 12.2 nightly-down

끄는 걸 잊어 밤새 과금되는 사고를 막는 안전장치다.

| 항목 | 내용 |
|---|---|
| 워크플로 | GitHub Actions `nightly-down.yml` ([CI/CD 3](06-cicd.md#3-워크플로-목록)) |
| 실행 | 매일 03:00 KST 예약 실행, 수동 실행(`workflow_dispatch`)도 지원 |
| 하는 일 | `make down` |
| 역할 | `fitjob-gha-env-down` — 온디맨드 스택 destroy 권한만 ([5.2](#52-cicd-역할-github-oidc)) |
| 멈추기 | 저장소 변수 `NIGHTLY_DOWN`이 `off`면 건너뛴다. 24시간 운영하는 운영 단계(W12~14)에는 `off`, 개발 기간에는 `on`. 03:00을 넘겨 작업할 때도 그날만 `off`로 바꾼다 |
| 실패 시 | GitHub Actions 실패 알림 메일 → [운영 RB-08](08-operations.md#rb-08-make-updown-실패--꺼지지-않은-리소스) |

### 12.3 운영 규칙

- 앱 개발은 최대한 로컬(docker compose + `BEDROCK_MODE=stub`)에서 하고, AWS는 인프라 작업과 통합 확인 때만 켠다.
- 작업이 끝나면 `make down`. 다음 날 아침 Cost Explorer로 밤사이 비용을 확인한다([운영 9](08-operations.md#9-비용-관리)).
- RDS는 Phase 2(데이터 파이프라인) 동안 계속 켜둔다(`rds_ephemeral = false`, 월 약 $21). 여러 날의 DB 상태가 이어져야 확인되는 적재 로직을 만드는 단계라서다([8.1](#81-rds-postgresql)). Phase 3부터는 `true`로 바꿔 `make up`·`make down`에 포함해도 된다.
- 수집은 개발 기간에도 매일 05:00 `collect_only`로 돌아 S3에 쌓인다. 작업할 때 `make up` 후 필요한 날짜를 replay해 DB에 넣는다.
- 운영 단계로 전환할 때: `asg_min`/`asg_desired`/`asg_max` = 1/1/4, `schedule_mode = full`, `observability` 켜기, `rds_ephemeral = false`(백업·삭제 보호), 저장소 변수 `NIGHTLY_DOWN = off`·`ENV_PHASE = ops`([CI/CD 5](06-cicd.md#5-aws-인증-github-oidc)). 부하 테스트·장애 훈련 기간에만 2/2/4로 올린다.
- 운영이 끝나면 `make down`으로 내리고, 면접·데모 때 `make up`으로 약 20분 안에 다시 띄운다.

### 12.4 주의 사항

| 항목 | 내용 |
|---|---|
| Secrets Manager 복구 대기 | 시크릿을 지우면 복구 대기 기간(7~30일) 동안 같은 이름으로 다시 만들 수 없다. 그래서 시크릿은 상시 `storage` 스택에 둔다. RDS 마스터 시크릿은 RDS가 매번 다른 이름으로 만들어서 예외다 |
| ALB DNS 변경과 `origin` 레코드 | ALB를 다시 만들면 DNS 이름이 바뀐다. `origin.<도메인>` 레코드를 `app` 스택에 둬서 ALB와 함께 만들고 지운다. CloudFront는 `origin.<도메인>`을 바라보므로 고칠 필요가 없다. `app`이 꺼져 있으면 웹 화면은 뜨고 `/api/*`는 502를 돌려준다 |
| 보안 그룹 위치 | 모든 보안 그룹은 `network`에 둔다. 온디맨드 스택에 두면 다른 스택의 규칙이 참조하고 있어 destroy가 의존성 오류로 멈춘다([3장](#3-보안-그룹)) |
| 수집 스케줄 | 개발 중에는 `schedule_mode = collect_only`. `full`로 두면 RDS·NAT가 꺼진 05:00에 적재가 실패하고 알림만 쌓인다. `collect_only`는 S3까지만 가므로 꺼져 있어도 성공한다. 적재는 작업할 때 replay로 한다 |

## 13. 콘솔 구축 후 Terraform으로 가져오기

학습을 위해 스택마다 AWS 관리 콘솔(웹 화면)로 먼저 만들고, 그 결과를 Terraform으로 가져온다([ADR-012](10-adr.md#adr-012-인프라를-콘솔로-먼저-만들고-terraform으로-가져온다)). 이 문서의 1~12장은 가져온 뒤의 최종 상태다. 콘솔로 만들 때도 이 설정을 기준으로 한다.

### 13.1 절차

| 단계 | 할 일 | 끝난 기준 |
|---|---|---|
| ① 콘솔 구축 | 1~12장 설정대로 콘솔에서 만든다. 설정값을 메모하고 화면을 캡처한다 | 동작 확인 (예: NAT 경유 외부 통신) |
| ② 코드 작성·import | 리소스 ID를 `import` 블록에 적고 `terraform plan -generate-config-out=generated.tf`로 초안을 받는다. 초안을 그대로 쓰지 않고 모듈·변수로 정리한다 | `terraform apply`로 import 완료 |
| ③ 차이 맞추기 | `plan`에 나오는 차이를 하나씩 코드 쪽에서 맞춘다. 콘솔 기본값이 의도와 다르면 이때 코드로 바로잡는다 | `terraform plan`이 "No changes" |
| ④ 재현 확인 | 지워도 되는 스택은 destroy 후 apply로 코드만으로 다시 만든다. 온디맨드 스택은 `make down`·`make up` | 다시 만든 것으로 같은 동작 확인 |
| ⑤ 전환 | 이후 변경은 코드로만 한다. `ManagedBy` 태그가 `terraform`으로 바뀌고 드리프트 점검 대상이 된다 | 콘솔에서 만든 리소스 중 state에 없는 것 0개 |

```hcl
# import 블록 예: 콘솔로 만든 VPC를 가져온다
import {
  to = aws_vpc.main
  id = "vpc-0abc1234"
}
```

- `-generate-config-out` 초안에는 읽기 전용 속성이나 서로 충돌하는 인자가 섞여 있다. 학습용 출발점으로만 쓰고 직접 다시 정리한다.
- `import` 블록은 가져온 뒤 지워도 되고 남겨도 해가 없다.
- Phase 1~3에는 아직 CI/CD가 없으므로 plan·apply는 로컬에서 한다. CI/CD를 만든 Phase 4부터는 6장 흐름을 따른다.

### 13.2 콘솔 단계 규칙

| 규칙 | 이유 |
|---|---|
| 이름은 `fitjob-prod-<역할>`, 태그는 `Project`, `Env`, `Stack`, `ManagedBy=console`을 처음부터 붙인다 | 비용 추적과 남은 리소스 검색에 쓴다. 가져오면 Terraform `default_tags`가 `ManagedBy=terraform`으로 바꾼다 |
| 시간당 과금 리소스(NAT, RDS, ALB, 앱 EC2)는 만든 날 import까지 끝내거나, 작업이 끝나면 직접 지운다 | 가져오기 전에는 state에 없어서 `make down`과 nightly-down이 지우지 못한다 |
| 마법사보다 리소스를 하나씩 만든다. 마법사를 썼다면 자동으로 생긴 리소스를 확인해 import하거나 지운다 | 아래 표의 리소스가 몰래 생긴다 |
| 시크릿은 틀(`aws_secretsmanager_secret`)만 import하고 값(`aws_secretsmanager_secret_version`)은 import하지 않는다 | 값이 state에 평문으로 남는다 |
| 기본 보안 그룹, 기본 라우팅 테이블, 기본 NACL은 `aws_default_*` 리소스로 다룬다 | VPC를 만들면 자동으로 생기고 지울 수 없다 |
| Lambda 코드는 콘솔 편집기로 고치지 않는다 | 코드는 저장소에서 패키징해야 재현된다 |

콘솔이 자동으로 만드는 리소스:

| 어디서 | 자동으로 생기는 것 | 대응 |
|---|---|---|
| VPC "VPC 등" 마법사 | 서브넷, 라우팅 테이블, IGW, 엔드포인트 | NAT Gateway 옵션은 반드시 "없음"(월 약 $32). 생긴 것은 모두 import |
| EC2 인스턴스 시작 마법사 | `launch-wizard-N` 보안 그룹 | 3장의 보안 그룹을 미리 만들어 고르고, 생겼으면 지운다 |
| RDS 생성 | "EC2 컴퓨팅 리소스에 연결"을 고르면 보안 그룹 2개 | 이 옵션을 고르지 않는다 |
| Lambda 생성 | 이름이 자동으로 붙는 실행 역할, 로그 그룹 | 5.1의 역할을 미리 만들어 고른다 |
| ACM DNS 검증 | Route 53 검증 레코드 | import 대상에 넣는다 |
| Route 53에서 도메인 구매 | 호스팅 영역 | `edge` 스택으로 import한다 |

### 13.3 스택별 진행

| 스택 | 콘솔로 만드는 것 | ④ 재현 확인 | 비고 |
|---|---|---|---|
| `bootstrap` | state 버킷, GitHub OIDC 공급자·역할, Budgets, 공용 SNS 토픽 | 하지 않음 (state 버킷을 지울 수 없음) | 처음에는 로컬 state로 import한 뒤 S3 백엔드로 옮긴다 |
| `network` | VPC, 서브넷, 라우팅 테이블, IGW, S3 엔드포인트, 보안 그룹 | destroy 후 apply. 다른 스택을 만들기 전에 한다 | 학습 효과가 가장 크다. 처음 해보기에 적합 |
| `nat` | NAT 인스턴스(소스/대상 확인 끄기, user data), `rt-app` 기본 경로. Phase 2에 DB 접속용 임시 EC2와 그 역할 | `make down`·`make up` | 임시 EC2는 Phase 3에서 지운다([8.5](#85-db-접속용-임시-ec2-phase-2)) |
| `storage` | S3 버킷, 시크릿(틀만), S3 Vectors, KB, ECR, SSM 파라미터 | 하지 않음 (데이터, 시크릿 복구 대기 기간) | S3 Vectors·KB는 프로바이더가 지원한다([요구사항 Q-06](01-requirements.md#9-미결-사항-구현-전-확인)). import가 막히는 부분만 CLI 스크립트로 보완 |
| `database` | DB 서브넷 그룹, 파라미터 그룹, RDS | 데이터를 넣기 전에 destroy 후 apply 1회 | |
| `pipeline` | Scheduler, Step Functions(Workflow Studio로 설계 후 정의 JSON을 내보내 코드로) | destroy 후 apply | Lambda는 콘솔에서 서비스만 익히고, 코드는 처음부터 저장소에서 패키징 |
| `edge` | 호스팅 영역(도메인 구매 시 생김), ACM 인증서 2개, CloudFront, OAC | 하지 않음 (호스팅 영역을 다시 만들면 네임서버가 바뀜) | CloudFront는 설정이 커서 설정 자동 생성이 특히 유용 |
| `app` | 대상 그룹, ALB, 리스너 규칙, 시작 템플릿, ASG, `origin` 레코드 | `make down`·`make up` | 리소스가 많아 시간이 가장 오래 걸린다 |
| `observability` | 알람, 대시보드, Route 53 헬스체크 | destroy 후 apply | |
