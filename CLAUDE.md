# FitJob (가칭)

여러 채용 소스(사람인 API, 공공데이터포털 공공기관 채용정보 API)의 공고를 모으고, 채팅으로 상황을 말하면 조건에 맞는 공고만 보여주는 서비스.
**클라우드 인프라 직무 포트폴리오**가 목적이라, 서비스 기능보다 AWS 인프라를 설계·구축·운영하고 결정과 결과를 수치로 남기는 것이 우선이다.

## 반드시 읽을 문서 (작업 유형별)
- 무엇을 만드는가, 범위, 미결 사항: docs/01-requirements.md
- 전체 구조, 장애 영향, 비용: docs/02-architecture.md
- DB 테이블, S3·KB 문서 형식, replay: docs/03-db-schema.md
- API, 채팅 조건 추출 스키마, 매칭 이유: docs/04-api-spec.md
- AWS 리소스, IAM, Terraform 스택, 온디맨드 운영, 콘솔 → import 절차: docs/05-infrastructure.md
- CI/CD 워크플로, 배포·롤백: docs/06-cicd.md
- 테스트, 데이터 품질 규칙, RAG 평가, 장애 훈련: docs/07-test-plan.md
- SLO, 알람, 런북: docs/08-operations.md
- 현재 단계와 일정: docs/09-roadmap.md
- 결정의 이유: docs/10-adr.md
- 하네스(권한·훅·검증 규칙, 단계별 구축 순서, 실수 → 규칙 기록): docs/harness.md
- 웹 UI: docs/design-system/README.md (Wanted Design System. React로 구현할 때 montage-react 스킬 참고)

## 현재 단계: Phase 0 준비 진행 중 (2026-11-04 앞당겨 시작)
- 설계 문서 01~10 v0.2 완료. 코드 없음. 공개 저장소 github.com/soyeun0327/fitjob (`main` 보호 설정 예정).
- W0: 사람인 API 심사 중, 공공기관 채용정보 API 키 활성화됨(2026-11-03, 코드 매핑 → DB 스키마 7.1, ADR-013), AWS Budgets 월 $100 알림 만듦(Phase 1에서 import)
- Phase 0 끝낸 것: 계정 보안, WSL 도구와 `aws login --remote`(`soyeun-admin`), 저장소·하네스, Q-06. 남은 것: import 연습, Q-03·Q-04·Q-05, Budgets 메일 확인
- 전체 일정 14주 (2026-11-09 ~ 2027-02-14). 단계별 작업과 완료 기준은 docs/09-roadmap.md
- 작업을 끝내면 docs/09-roadmap.md 7장 완료 기록에 날짜·작업·커밋을 남긴다

## 설계 원칙 (어기면 안 되는 것)
- **하드 조건은 필터로.** 경력·지역·직무·고용형태·학력·마감은 KB 메타데이터 필터와 RDS 재확인으로 거른다. 벡터 유사도나 LLM 판단에 맡기지 않는다 (ADR-003)
- **공고의 최종 기준은 RDS.** KB는 후보를 찾는 색인일 뿐이다. 채팅 결과는 RDS에서 `ACTIVE`를 다시 확인한다
- **LLM 출력은 믿지 않는다.** 조건 추출은 enum이 고정된 도구 스키마로만 받는다. 원문 URL은 서버가 RDS 값으로 채운다. 공고에 없는 정보를 지어내지 않는다
- **공식 API만 쓴다.** 크롤링 금지, 모든 공고에 출처와 원문 링크 (ADR-001)
- **비밀값은 평문으로 두지 않는다.** 코드·이미지·Terraform 변수·state 모두. 시크릿 값은 import하지 않는다
- **앱 서버 권한은 최소로.** 앱 EC2 역할은 `db-app` 시크릿만 읽는다. 마이그레이션과 DB 사용자 생성은 배포 러너나 운영자 PC에서 SSM 포트 포워딩으로 한다
- **상시 스택은 온디맨드 스택을 Terraform으로 참조하지 않는다.** DB 주소는 SSM 파라미터 `/fitjob/prod/db/endpoint`로 넘긴다. 보안 그룹은 모두 `network`, 시크릿과 앱 SSM 파라미터는 `storage`에 둔다
- **이름과 태그.** 리소스 이름 `fitjob-prod-<역할>`, 태그 `Project`·`Env`·`ManagedBy`·`Stack`
- **콘솔로 먼저 만들고 Terraform으로 가져온다 (ADR-012).** 가져온 뒤에는 콘솔 수동 변경 금지
- **마이그레이션은 하위 호환으로.** 확장 → 전환 → 축소 순서, 되돌리지 않고 앞으로만 고친다
- **비용 예산.** 개발 기간 월 $35 이하, 운영 단계 월 $100 이하. 시간당 과금 리소스는 온디맨드 스택(`nat`, `database`, `app`, `observability`)에 둔다

## AWS 작업 규칙 (Claude가 작업할 때)
- 리전은 서울 `ap-northeast-2`. CloudFront 인증서와 Route 53 헬스체크 알람만 `us-east-1`
- `terraform plan`, `aws ... describe/list/get` 같은 읽기는 해도 된다
- `terraform apply`·`destroy`, AWS CLI 쓰기 명령, `make up`·`make down`은 사용자가 요청할 때만 실행한다. 실행 전에 대상 스택과 비용 영향을 말한다
- 온디맨드 스택을 켰다면 작업이 끝날 때 `make down`을 할지 사용자에게 묻는다
- `rds_ephemeral = false`인 동안 `database` 스택을 destroy하지 않는다
- 콘솔로 만들고 아직 가져오지 않은 리소스는 `make down`이 지우지 못한다. `ManagedBy=console` 태그로 남은 것을 확인한다

## 문서 수정 규칙
- 문서는 한국어, 짧은 문장, "~다" 체. 표를 적극적으로 쓴다
- 문서 간 숫자·이름을 맞춘다. 특히 비용, ASG 대수(기본 1/1/4, 훈련 2/2/4), 스택 9개(상시 5 + 온디맨드 4), 시크릿 5개, 워크플로 12개, 일정 14주. 하나를 바꾸면 관련 문서를 전부 찾아 고친다
- 고친 문서는 상단 버전 표에 `변경` 행을 추가한다
- 상대 링크와 섹션 앵커(GitHub 규칙)가 깨지지 않았는지 확인한다: `wsl -e python3 scripts/check_doc_links.py` (`.md` 수정 시 훅이 자동 실행)
- 결정을 바꾸면 ADR을 지우지 않는다. 상태를 `대체됨`(또는 `일부 대체됨`)으로 바꾸고 새 ADR을 추가한다
- 애매한 부분은 고치기 전에 묻는다

## 작업 완료 조건 (구현 시작 후)
도구는 Phase 0~4에서 만든다(docs/harness.md 7장). 실제 명령어가 생기면 이 절을 갱신한다.
같은 유형의 실수가 반복되면 프롬프트 대신 규칙·훅·테스트를 추가하고 docs/harness.md 8장에 기록한다.
- 앱(`app/`): ruff, mypy, pytest(PostgreSQL 컨테이너) 통과
- 웹(`web/`): lint, 단위 테스트, build 통과
- 인프라(`infra/`): `terraform fmt -check`, `validate`, `tflint`, `checkov` 통과, 바뀐 스택 `plan` 확인. 콘솔에서 가져온 스택은 `plan` "No changes"
- 프롬프트 변경: RAG 평가 프롬프트 모드 통과(조건 추출 정확도 90% 이상, 거절 정확도 100%)

## 명령어 (계획)
- 온디맨드 스택: `make up` / `make down` / `make up-app` / `make down-app` (`infra/Makefile`)
- 로컬 개발: `docker compose`(PostgreSQL) + `uvicorn`, `BEDROCK_MODE=stub`이면 LLM·KB 호출을 고정 응답으로 대체
- 개발 PC는 Windows, 명령은 WSL(Ubuntu 24.04)에서 실행한다. make·Terraform·AWS CLI·Session Manager 플러그인과 make가 부르는 검사 도구는 WSL에만 둔다(Docker는 Docker Desktop WSL 연동)
- Claude는 `wsl -e <명령>`으로 실행하고 경로는 상대 경로로 준다. Windows에서 직접 실행하지 않는다 (docs/harness.md 2-1)

## 저장소 구조 (계획)
```
app/        FastAPI API 서버 (Dockerfile)
pipeline/   Lambda: collector, normalizer, loader, finalizer
web/        React + Vite
infra/      Terraform (modules/, stacks/ 9개, Makefile)
tests/      e2e/ (Playwright), load/ (k6), rag-eval/
scripts/    배포, 마이그레이션, 스모크, 보안 회귀
docs/       설계 문서
```

## Git 워크플로우

### 브랜치 전략
- GitHub Flow: `main` + 기능 브랜치(`feat/…`, `fix/…`, `infra/…`). 모든 변경은 PR로
- `main` 보호: PR 필수, 필수 상태 검사 통과, 강제 푸시 금지, 스쿼시 병합
- 혼자 개발해도 PR을 쓴다. PR 설명과 plan 댓글이 작업 기록이 된다

### 작업 단위 흐름
1. 파악: 관련 docs와 영향 파일 확인, 불명확한 요구사항은 작업 전에 질문
2. 구현: 작업 완료 조건 통과 확인
3. 커밋: `git add <구체적 파일>` (`git add .` 사용 안 함)
4. PR/merge: 명시적으로 요청할 때만

### 커밋 타이밍
- Phase 안의 작업 단위(로드맵 표의 행)마다 커밋 1회

### 규칙
- 커밋/푸시는 명시적 요청 시에만
- force push, reset --hard 등 파괴적 작업은 요청해도 한 번 더 확인
- 커밋 메시지: Conventional Commits `type: 설명` (feat / fix / infra / chore / refactor / test / docs)
