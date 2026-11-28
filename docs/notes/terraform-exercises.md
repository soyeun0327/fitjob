# Terraform 실습 모음

| 항목 | 내용 |
|---|---|
| 문서 버전 | v0.1 |
| 작성일 | 2026-11-25 |
| 목적 | [기초 노트](terraform-basics.md) 다음 단계. Phase 1(`bootstrap`·`network`·`nat`)에서 쓸 기술을 무료 리소스로 미리 연습한다([로드맵 Phase 1](../09-roadmap.md#phase-1-기반-인프라-w46)) |
| 쓰는 법 | 실습마다 과제를 읽고 **먼저 직접 코드를 쓴다.** 막히면 힌트를, 그래도 막히면 접어 둔 정답 코드를 연다. 명령은 사용자가 직접 실행하고, Claude는 코드와 plan 결과를 검토한다 |
| 검증 | 정답 코드는 Terraform 1.17.1·AWS 프로바이더 6.74.0에서 `fmt -check`, `validate`를 통과했고, 실습 1·3·4·5·8·10의 plan 개수를 확인했다(2026-11-25, 리소스는 만들지 않음) |
| 변경 | 연습 폴더를 `C:\Users\soyeun\workspace\tf-practice`로 옮김, 1.2에 프로바이더 캐시 명령 설명 추가(실습 모음 페이지에서 고친 내용 반영) (2026-11-25) |
| 변경 | 1.2 캐시 설명 고침: lock 파일이 없는 새 폴더는 다시 내려받는다(디스크에는 한 벌만 남음) (2026-11-25) |
| 변경 | 1.6 AWS 프로바이더와 Registry 문서 읽는 법 추가, 1.5에 인자 오류 2행 추가, 실습 1·6에서 1.6 연결 (2026-11-26) |
| 변경 | 실습 3에 참고 메모 3개 추가: `variables.tf`의 역할과 이름, `var.` 접두어, `data.` 접두어(실습 모음 페이지에서 추가한 내용 반영) (2026-11-26) |
| 변경 | 실습 4 다음에 기초 연습 문제 5개 추가. 정답 코드 `fmt -check`·`validate`, 처음 plan 개수, 오류 메시지를 실제 출력으로 확인 (2026-11-28) |
| 변경 | 실습 4에 참고 메모 3개 추가: `aws_ssm_parameter`, `count.index`, `each.key`·`each.value`(실습 모음 페이지에서 추가한 내용 반영, 오타 1곳 고침) (2026-11-28) |

---

## 1. 시작하기 전에

### 1.1 실습 순서

| # | 실습 | 배우는 것 | 이어지는 실제 작업 | 시간 | 비용 |
|---|---|---|---|---|---|
| 1 | [코드로 만들고 지우기](#실습-1-코드로-만들고-지우기) | 리소스 참조, 의존 순서, 교체(`-/+`), destroy | 모든 스택 | 30분 | 0 |
| 2 | [콘솔 버킷 가져오기](#실습-2-콘솔-버킷-가져오기) | import, 드리프트 | 모든 스택. **Phase 0 남은 작업** | 1시간 | 0 |
| 3 | [변수와 출력](#실습-3-변수와-출력) | variable, tfvars, locals, data, output | 모든 스택 | 40분 | 0 |
| 4 | [count와 for_each](#실습-4-count와-for_each) | 같은 리소스 여러 개, 주소 모양 | 서브넷 6개, SSM 파라미터 | 30분 | 0 |
| 5 | [미니 network 스택](#실습-5-미니-network-스택) | VPC, 서브넷, 라우팅, 보안 그룹 | `network` | 1시간 30분 | 0 |
| 6 | [state를 S3로 옮기기](#실습-6-state를-s3로-옮기기) | S3 백엔드, 잠금, `prevent_destroy` | `bootstrap` | 1시간 | 1센트 미만 |
| 7 | [스택 나누기](#실습-7-스택-나누기) | `terraform_remote_state`, 경로를 누가 갖나 | `nat` ↔ `network` | 40분 | 0 |
| 8 | [콘솔 VPC 가져오기와 재현](#실습-8-콘솔-vpc-가져오기와-재현) | 여러 리소스 import, 초안 정리, destroy 후 apply | `network` ①~④ | 1시간 30분 | 0 |
| 9 | [드리프트와 state 다루기](#실습-9-드리프트와-state-다루기) | `-detailed-exitcode`, `-refresh-only`, `moved`, `removed` | 매일 드리프트 점검 | 1시간 | 0 |
| 10 | [모듈로 정리하기](#실습-10-모듈로-정리하기) | module, 입력·출력, 모듈 안으로 옮기기 | `infra/modules/` | 1시간 | 0 |
| 11 | [온디맨드 EC2와 SSM 접속 (선택)](#실습-11-온디맨드-ec2와-ssm-접속-선택) | AMI 조회, IAM 역할, IMDSv2, SSM 접속 | `nat`, `app` | 1시간 | 약 1~2센트 |
| 12 | [정리](#4-실습-12-정리) | 역순 삭제, 남은 리소스 확인 | `make down`, RB-08 | 30분 | 0 |

- 합계 약 10시간이다. **Phase 0 완료에 필요한 것은 실습 2(기초 노트 8장)뿐이다.** 실습 5~11은 Phase 1에서 콘솔 구축을 시작하기 전까지 하면 된다.
- 실습 4 다음에 [기초 연습 문제](#기초-연습-문제) 5개가 있다. 실습 1~4의 개념을 정답을 보지 않고 다시 써 보는 선택 과제다. 약 2시간 30분 걸리고 비용은 없다.
- 실습 5·6에서 만든 것(연습 VPC, state 버킷)은 실습 7~11에서 계속 쓴다. 무료라 켜 두어도 되고, 실습 12에서 한꺼번에 지운다.
- 비용은 실습 11만 든다. t4g.nano는 서울에서 시간당 $0.0052(Pricing API로 2026-11-25 확인)이고, 퍼블릭 IPv4가 시간당 $0.005다. 1시간 안에 지우면 2센트를 넘지 않는다.

### 1.2 폴더 구조

실습마다 폴더를 따로 쓴다. **폴더 하나 = state 하나 = 스택 하나**다. 저장소 밖에 둔다(Phase 1부터 `infra/`에 구조 테스트와 tflint가 붙는다).

```
C:\Users\soyeun\workspace\tf-practice\    WSL 경로: /mnt/c/Users/soyeun/workspace/tf-practice
├── 01-first-resource/
├── 02-import/            ← 기초 노트 8장
├── 03-variables/
├── 04-count-foreach/
├── 05-network/           ← 실습 7부터 state를 S3에 둔다. 실습 10에서 modules/ 추가
├── 06-state-bucket/
├── 07-ondemand/          ← 실습 11의 EC2도 여기
└── 08-console-vpc/       ← 실습 9도 여기서
```

AWS 프로바이더는 폴더마다 약 800MB를 차지한다(6.74.0 기준 775MB). 캐시를 켜 두면 원본은 캐시에 한 벌만 두고 폴더에는 바로가기만 생긴다(`/mnt/c` 폴더에서도 되는 것을 2026-11-25에 확인했다). 다만 lock 파일이 없는 새 폴더에서는 체크섬을 적으려고 다시 내려받는다. 아끼는 것은 디스크다. 확인하는 법과 다운로드를 건너뛰는 법은 [질문 기록 Q14](qa-log.md#q14-terraformrc에-캐시-폴더를-설정하고-terraform-init을-했는데-프로바이더가-캐시에-저장됐는지-어떻게-확인해)에 있다. WSL 터미널에서 한 번만 실행한다.

```bash
mkdir -p ~/.terraform.d/plugin-cache
echo 'plugin_cache_dir = "$HOME/.terraform.d/plugin-cache"' > ~/.terraformrc
```

1. `mkdir -p ~/.terraform.d/plugin-cache`
   - 내려받은 프로바이더를 모아 둘 폴더(캐시)를 만든다.
   - `~`는 홈 폴더(`/home/soyeun` 같은 곳)다.
   - `-p`를 붙이면 중간 폴더(`.terraform.d`)가 없을 때 같이 만들고, 이미 있어도 오류를 내지 않는다.
2. `echo '...' > ~/.terraformrc`
   - 따옴표 안의 한 줄을 `~/.terraformrc` 파일에 쓴다. 이 파일은 Terraform 전체에 적용되는 설정 파일이다.
   - `plugin_cache_dir = "..."`는 "프로바이더는 이 캐시 폴더에서 꺼내 써라"라는 뜻이다.
   - `>`는 파일을 **새로 쓴다**. 원래 있던 내용은 지워진다. 처음 설정할 때는 괜찮지만, `.terraformrc`에 이미 다른 설정이 있었다면 `>>`(뒤에 덧붙이기)로 쓴다.
   - 작은따옴표라서 `$HOME`이 셸에서 풀리지 않고 글자 그대로 파일에 들어간다. Terraform이 설정 파일을 읽을 때 홈 폴더로 바꿔 준다.

### 1.3 공통 코드

모든 폴더의 `main.tf` 맨 위에 둔다. 기초 노트 4장과 같고, `Stack`만 `practice`다.

```hcl
terraform {
  required_version = ">= 1.11"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

provider "aws" {
  region = "ap-northeast-2"
  default_tags {
    tags = { Project = "fitjob", Env = "prod", ManagedBy = "terraform", Stack = "practice" }
  }
}
```

| 규칙 | 이유 |
|---|---|
| 이름은 `fitjob-practice-<역할>` | Phase 1의 진짜 리소스 이름(`fitjob-prod-vpc` 등)과 겹치지 않게 |
| 연습 VPC 대역은 `10.1.0.0/16`, `10.2.0.0/16` | 진짜 VPC(`10.0.0.0/16`)와 헷갈리지 않게 |
| 태그 `Stack = "practice"` | 실습 12에서 남은 것을 이 태그로 찾는다 |
| `<계정ID>`는 12자리 계정 번호로 바꿔 쓴다 | 공개 저장소라 문서에는 적지 않는다. `aws sts get-caller-identity --query Account --output text` |

### 1.4 매번 하는 순서

| 순서 | 명령 | 왜 |
|---|---|---|
| 1 | `terraform fmt` | 들여쓰기 정리. 실제 스택에서는 `fmt -check`가 CI 검사다 |
| 2 | `terraform validate` | 오타·인자 이름 검사(AWS 접속 없음) |
| 3 | `terraform plan` | **마지막 요약 줄부터 읽는다.** 예상과 다르면 멈춘다 |
| 4 | `terraform apply` → 요약 줄을 다시 확인하고 `yes` | |

### 1.5 막혔을 때

| 증상 | 원인 | 해결 |
|---|---|---|
| `No valid credential sources found`, `ExpiredToken` | 로그인 만료 | `aws login --remote` |
| `BucketAlreadyExists` | 버킷 이름은 전 세계에서 하나뿐이어야 한다 | 이름 끝에 계정 번호 |
| `Error acquiring the state lock` | 다른 터미널에서 실행 중이거나, 비정상 종료로 잠금이 남음 | 다른 실행이 없는지 확인한 뒤 `terraform force-unlock <잠금 ID>`(ID는 오류에 나온다) |
| `Backend initialization required` | backend 블록을 바꿨다 | `terraform init -migrate-state` |
| `Module not installed` | module 블록을 추가했다 | `terraform init` |
| `Cannot import non-existent remote object` | import 블록의 ID가 가리키는 리소스가 없다 | ID를 다시 확인하거나, 이미 끝난 import 블록을 지운다 |
| 보안 그룹 `InvalidParameterValue` | 보안 그룹 설명(description)에 한글이 있다 | 설명은 영어로 쓴다 |
| plan에 예상 밖의 `-/+`·destroy | — | apply하지 않는다. plan 결과를 Claude에게 붙여 넣는다 |
| `Unsupported argument`(`An argument named "..." is not expected here`) | 인자 이름 오타, 또는 `latest` 문서에만 있는 새 인자 | lock 파일 버전의 문서에서 이름을 다시 찾는다([1.6](#16-aws-프로바이더와-registry-문서)) |
| `Missing required argument`, `Insufficient ... blocks` | `Required` 인자나 블록을 빠뜨렸다 | 문서 Argument Reference에서 `Required` 표시를 확인한다 |

### 1.6 AWS 프로바이더와 Registry 문서

**Terraform Registry**(registry.terraform.io)는 프로바이더와 모듈을 올려 두는 공개 저장소다. `terraform init`은 여기서 프로바이더를 내려받고, 사람은 여기서 리소스 설명서를 읽는다. "인자 이름이 뭐였지?" 할 때 가장 먼저 여는 곳이다. 아래 내용은 2026-11-26에 Registry API와 문서 원본으로 확인했다.

**코드와 Registry가 이어지는 곳**

| 코드·파일 | 뜻 |
|---|---|
| `source = "hashicorp/aws"` | Registry의 `<만든 곳>/<이름>`이다. 앞의 `registry.terraform.io/`가 생략되어 있다. lock 파일에는 `registry.terraform.io/hashicorp/aws`처럼 전체 주소로 적힌다 |
| `version = "~> 6.0"` | 6.0 이상 7.0 미만 중 최신을 고른다. 지금 최신은 6.74.0(2026-11-23 공개)이다 |
| `.terraform.lock.hcl`의 `version = "6.74.0"` | `init`이 실제로 고른 버전이다. 다음 `init`도 이 버전을 쓴다. **문서도 이 버전으로 본다** |
| `terraform init -upgrade` | lock 파일의 버전을 무시하고 조건(`~> 6.0`) 안의 최신으로 바꾼다 |

- AWS 프로바이더 등급은 `official`이다. HashiCorp가 직접 관리한다는 뜻이다.
- 소스 코드와 문서 원본은 GitHub `hashicorp/terraform-provider-aws`에 있다.

**문서 주소 규칙**

리소스 종류 이름에서 앞의 `aws_`를 떼면 주소 끝이 된다. 규칙을 알면 검색 없이 바로 연다.

| 찾는 것 | 주소 |
|---|---|
| 프로바이더 첫 화면 | `https://registry.terraform.io/providers/hashicorp/aws/latest/docs` |
| 리소스 `aws_s3_bucket` | `.../aws/latest/docs/resources/s3_bucket` |
| 데이터 소스 `aws_caller_identity` | `.../aws/latest/docs/data-sources/caller_identity` |
| 내 버전(6.74.0)의 문서 | 주소의 `latest`를 `6.74.0`으로 바꾼다 |

- `latest`는 가장 최근 버전의 문서다. 몇 달 지나 lock 파일 버전이 뒤처지면, `latest` 문서에는 있지만 내 버전에는 없는 인자가 생긴다. 그러면 `Unsupported argument` 오류가 난다. 이때는 버전을 맞춘 문서를 본다.
- 문서는 서비스별로 묶여 있다. 예를 들어 `aws_s3_bucket`·`aws_s3_bucket_versioning`은 `S3 (Simple Storage)`, `aws_caller_identity`는 `STS (Security Token)` 아래에 있다.
- 콘솔의 설정 하나가 리소스 하나와 꼭 같지는 않다. 콘솔에서는 버킷 화면 안의 "버전 관리"가 Terraform에서는 별도 리소스 `aws_s3_bucket_versioning`이다. 이름을 모르면 서비스 묶음을 펼쳐 훑거나 `versioning` 같은 키워드로 찾는다.
- Registry 화면이 안 열리면 GitHub 문서 원본을 본다. 리소스는 `website/docs/r/<이름>.html.markdown`, 데이터 소스는 `website/docs/d/<이름>.html.markdown`이다(`<이름>`은 `aws_`를 뗀 것). `main` 브랜치에는 아직 나오지 않은 변경이 섞일 수 있다. 버전을 맞추려면 `v6.74.0` 태그로 본다.

**리소스 문서의 절**

`aws_s3_bucket` 문서는 아래 순서다. 다른 리소스도 거의 같다.

| 절 | 담긴 것 | 언제 보나 |
|---|---|---|
| Example Usage | 바로 쓸 수 있는 예시 코드 | 처음 쓸 때. 예시를 복사해 고치는 것이 가장 빠르다 |
| Argument Reference | **내가 코드에 쓰는 값**(인자). 중괄호 블록(`versioning_configuration { }` 같은 것)은 아래 `` `이름` Block `` 절에 따로 있다 | 인자 이름과 필수 여부를 찾을 때 |
| Attribute Reference | **만들어진 뒤 읽을 수 있는 값**(속성). 인자도 모두 읽을 수 있고, 여기에는 그 밖에 AWS가 정하는 값(`id`, `arn` 등)이 적혀 있다 | 다른 리소스에서 참조할 때(`aws_s3_bucket.this.id`) |
| Timeouts | 만들기·지우기를 얼마나 기다릴지 | 거의 안 본다 |
| Import | `import` 블록의 `id`에 무엇을 넣는지 | 콘솔 리소스를 가져올 때(실습 2·6·8) |

**인자 한 줄 읽는 법**

Argument Reference의 인자는 `` `이름` - (표시) 설명 `` 모양이다. 실제 `aws_s3_bucket` 문서의 줄(설명은 줄임)이다.

```
* `bucket` - (Optional, Forces new resource) Name of the bucket. If omitted, Terraform will assign a random, unique name.
* `force_destroy` - (Optional, Default:`false`) Boolean that indicates all objects ... should be deleted ...
* `versioning` - (Optional, **Deprecated**) ... Use the resource `aws_s3_bucket_versioning` instead.
* `region` - (Optional) Region where this resource will be managed. Defaults to the Region set in the provider configuration.
```

| 괄호 안 표시 | 뜻 | 실습 1에서 |
|---|---|---|
| `Required` | 반드시 쓴다. 빠지면 `validate`가 오류를 낸다 | `aws_s3_bucket_versioning`의 `versioning_configuration` 블록 |
| `Optional` | 안 써도 된다. 안 쓰면 기본값이나 AWS가 정한 값이 들어간다 | `bucket`을 빼면 Terraform이 임의의 이름을 붙인다 |
| `Forces new resource` | 바꾸면 고치지 못하고 지운 뒤 새로 만든다(`-/+`) | 6번에서 이름을 바꾸면 교체된다 |
| `Default:` | 안 쓰면 들어가는 값 | `force_destroy`가 `false`라서 8번에서 `BucketNotEmpty`가 난다 |
| `Deprecated` | 앞으로 나올 큰 버전(7.0 같은)에서 없어진다. 새 코드에 쓰지 않는다 | 버킷 안의 `versioning` 블록 대신 별도 리소스를 쓰는 이유 |

- `region`은 6.x부터 리전 리소스 대부분에 생긴 인자다. 이 리소스만 프로바이더와 다른 리전에 둘 때 쓴다. 이 실습에서는 쓰지 않는다.
- Attribute Reference에는 `` `id` - Name of the bucket. ``, `` `arn` - ARN of the bucket. ``이 있다. 그래서 `aws_s3_bucket.this.id`를 넘기면 버킷 이름이 들어간다.

**Import 절**

`aws_s3_bucket` 문서에는 두 가지 방법이 나온다.

```hcl
import {
  to = aws_s3_bucket.example
  id = "bucket-name"
}
```

```bash
terraform import aws_s3_bucket.example bucket-name
```

- 위는 `import` 블록이다. 코드에 남아 plan으로 미리 볼 수 있다. 이 프로젝트는 이 방법을 쓴다([기초 노트 4장](terraform-basics.md#4-연습-코드-한-줄씩)).
- 아래는 옛 방식인 명령이다. 실행하면 바로 state에 들어간다.
- `id`의 모양은 리소스마다 다르다. 버킷은 버킷 이름, VPC는 `vpc-0abc...`이다. 꼭 그 리소스의 Import 절을 본다.
- Terraform 1.12부터는 `id` 대신 `identity = { bucket = "bucket-name" }`로도 쓸 수 있다(문서의 Identity Schema 절). 설치된 1.17.1에서도 되지만, 이 실습은 `id`로 통일한다.

**데이터 소스 문서**

데이터 소스는 이미 있는 것을 **읽기만** 한다. 그래서 문서에 Import 절이 없다. `aws_caller_identity` 문서는 Example Usage, Argument Reference("This data source does not support any arguments."), Attribute Reference(`account_id`, `arn`, `id`, `user_id`)뿐이다. 실습 3에서 계정 번호를 읽을 때 쓴다.

**직접 찾아보기.** Registry에서 6.74.0 문서를 열고 답을 찾는다.

1. `aws_s3_bucket`에 `bucket`을 쓰지 않으면 어떻게 되나?
2. `aws_s3_bucket.this.arn`에는 어떤 모양의 값이 들어가나?
3. `aws_s3_bucket_versioning`을 import할 때 `id`에 무엇을 넣나?
4. `aws_caller_identity`로 계정 번호를 읽으려면 어떤 속성을 쓰나?

<details>
<summary>답</summary>

1. `Optional`이라 오류는 없다. Terraform이 임의의 고유 이름을 붙인다.
2. `arn:aws:s3:::버킷이름`
3. 버킷 이름이다. 버킷 주인 계정(`expected_bucket_owner`)을 지정했다면 `버킷이름,계정번호`처럼 쉼표로 잇는다.
4. `account_id`다. 이 데이터 소스에는 인자가 없다.

</details>

---

## 2. 기초 다지기 (실습 1~4)

### 실습 1. 코드로 만들고 지우기

| 항목 | 내용 |
|---|---|
| 목표 | 콘솔 없이 코드만으로 버킷을 만들고, 딸린 설정을 붙이고, 이름을 바꿔 교체를 보고, 지운다 |
| 폴더 | `01-first-resource/` |

**새 개념**

| 개념 | 뜻 |
|---|---|
| 참조 `aws_s3_bucket.this.id` | 다른 리소스의 값을 가져다 쓴다. `종류.이름.속성` 모양이다 |
| 암묵적 의존 | 참조하면 순서가 생긴다. 버킷을 먼저 만들고, 그 버킷을 참조하는 설정을 나중에 만든다. 참조가 없는 리소스끼리는 동시에 만든다 |
| `(known after apply)` | AWS가 만들어야 정해지는 값(ID, ARN). plan 때는 모른다 |
| 교체 `-/+` | 바꿀 수 없는 값(버킷 이름)을 바꾸면 지우고 새로 만든다 |

**과제.** `main.tf`에 공통 코드와 다음 3개를 쓴다.

1. 버킷 `fitjob-practice-first-<계정ID>` (`aws_s3_bucket`)
2. 그 버킷의 퍼블릭 접근 차단 4개를 모두 켠다 (`aws_s3_bucket_public_access_block`)
3. 그 버킷의 버전 관리를 켠다 (`aws_s3_bucket_versioning`)

힌트: 2·3번의 `bucket` 인자에 이름 문자열을 쓰지 말고 1번을 참조한다. 인자 이름은 [Terraform Registry](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)에서 리소스 이름으로 찾는다. 문서 읽는 법은 [1.6](#16-aws-프로바이더와-registry-문서)에 있다.

**실행**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 1 | `terraform init` | "successfully initialized" | |
| 2 | `terraform plan` | `Plan: 3 to add`. `id`, `arn`이 `(known after apply)` | AWS가 정하는 값 |
| 3 | `terraform apply` → `yes` | 버킷이 `Creation complete`된 뒤 나머지 둘이 만들어진다 | 참조가 순서를 만든다 |
| 4 | `terraform state list` | 주소 3개 | |
| 5 | S3 콘솔에서 버킷의 태그 확인 | 태그 4개 | 코드에 안 적어도 `default_tags`가 붙인다 |
| 6 | `bucket` 이름 끝에 `-v2`를 붙이고 `terraform plan` | 3개 모두 `-/+`와 `# forces replacement`. `3 to add, 0 to change, 3 to destroy` | 딸린 설정도 함께 교체된다 |
| 7 | `terraform apply` → `yes` | 옛 버킷이 지워지고 새 버킷이 생긴다 | 빈 버킷이라 괜찮다. 데이터가 있었다면 사고다 |
| 8 | S3 콘솔에서 새 버킷에 아무 파일이나 올리고 `terraform destroy` | `BucketNotEmpty` 오류로 멈춘다 | 기본값은 빈 버킷만 지운다 |
| 9 | 버킷에 `force_destroy = true`를 넣고 `apply` → `destroy` | `3 destroyed` | 연습용에서만 쓴다. 실제 데이터 버킷에는 쓰지 않는다 |

**생각해 볼 질문.** 2번의 `bucket = aws_s3_bucket.this.id`를 `bucket = "fitjob-practice-first-..."`처럼 문자열로 쓰면 어떻게 될까?

<details>
<summary>답</summary>

1. 참조가 없어 순서가 사라진다. Terraform이 둘을 동시에 만들다가, 버킷이 생기기 전에 설정을 붙이려 해서 `NoSuchBucket` 오류가 날 수 있다.
2. 6번처럼 이름을 바꿀 때 한 곳만 고치면 서로 다른 버킷을 가리킨다.

</details>

<details>
<summary>정답 코드 (공통 코드 아래)</summary>

```hcl
resource "aws_s3_bucket" "this" {
  bucket = "fitjob-practice-first-<계정ID>"
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

</details>

### 실습 2. 콘솔 버킷 가져오기

[기초 노트 8장](terraform-basics.md#8-직접-해-보기)을 `02-import/` 폴더에서 한다. Phase 0 로드맵의 남은 작업이다.

- 12번(비용 할당 태그 활성화)은 2026-11-25에 끝났으니 건너뛴다.
- 13번(`destroy`)까지 바로 해도 된다. 끝나면 로드맵 [7장 완료 기록](../09-roadmap.md#7-완료-기록)에 남긴다.

### 실습 3. 변수와 출력

| 항목 | 내용 |
|---|---|
| 목표 | 값을 코드에 박아 두지 않고 밖에서 받는다. 계정 번호를 코드에 적지 않는다 |
| 폴더 | `03-variables/` |

**새 개념**

| 블록·파일 | 뜻 | 비유 |
|---|---|---|
| `variable` | 밖에서 받는 입력값. 기본값이 없으면 반드시 받아야 한다 | 함수의 매개변수 |
| `terraform.tfvars` | 변수 값을 적는 파일. 이 이름이면 자동으로 읽는다 | 설정 파일 |
| `validation` | 값이 규칙에 맞지 않으면 plan 전에 멈춘다 | 입력 검사 |
| `locals` | 코드 안에서 여러 번 쓰는 계산값 | 지역 변수 |
| `data` | 이미 있는 것을 **읽기만** 한다. 만들지도 지우지도 않는다 | 조회 |
| `output` | 실행 뒤 보여 주는 값. 다른 스택이 읽어 가는 값이기도 하다(실습 7) | 함수의 반환값 |
| `"${...}"` | 문자열 안에 값을 끼워 넣는다 | |

Terraform은 폴더 안의 `*.tf` 파일을 모두 하나로 읽는다. 파일 이름은 관례일 뿐이다. 보통 `main.tf`, `variables.tf`, `outputs.tf`로 나눈다.

**과제**

1. `variables.tf`: `env`(기본값 `prod`, `prod`·`dev`만 허용), `stack`(기본값 `practice`), `purpose`(기본값 없음)
2. `main.tf`: 공통 코드의 `default_tags`에서 `Env`·`Stack`을 변수로 바꾼다. `data "aws_caller_identity"`로 계정 번호를 읽고, `locals`에서 버킷 이름 `fitjob-practice-<purpose>-<계정 번호>`를 만든다. 그 이름으로 버킷 하나를 만든다
3. `outputs.tf`: 버킷 이름, 버킷 ARN, 계정 번호
4. `terraform.tfvars`: 처음에는 만들지 않는다(실행 1번)

**실행**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 1 | `terraform.tfvars` 없이 `terraform plan` | `var.purpose  Enter a value:`로 묻는다. `Ctrl+C`로 멈춘다 | 기본값이 없는 변수 |
| 2 | `terraform.tfvars`에 `purpose = "vars"`를 쓰고 `terraform plan` | 버킷 이름이 계정 번호까지 보인다(`known after apply`가 아님) | data는 plan 때 읽는다 |
| 3 | `terraform plan -var 'env=staging'` | 내가 쓴 `error_message`로 멈춘다 | validation |
| 4 | `terraform apply` | 끝에 `Outputs:` 3개 | |
| 5 | `terraform output -raw bucket_name` | 이름만 한 줄 | 스크립트에서 값을 꺼내는 법(실습 5에서 쓴다) |
| 6 | `terraform plan -var 'env=dev'` | 버킷이 교체되지 않고 `~`. `Env` 태그만 `"prod" -> "dev"` | `default_tags`를 바꾸면 모든 리소스의 태그가 바뀐다 |
| 7 | `terraform console`에서 `local.bucket_name`, `cidrsubnet("10.1.0.0/16", 8, 11)`을 입력하고 `exit` | 이름, `"10.1.11.0/24"` | 식을 시험해 보는 곳. 실습 5의 서브넷 계산 |
| 8 | `terraform destroy` | `1 destroyed` | |

**변수 값의 우선순위** (아래로 갈수록 이긴다)

| 순서 | 출처 |
|---|---|
| 1 | `variable`의 `default` |
| 2 | 환경 변수 `TF_VAR_purpose=...` |
| 3 | `terraform.tfvars` |
| 4 | `*.auto.tfvars` |
| 5 | 명령의 `-var`, `-var-file` |

**생각해 볼 질문.** 기초 노트에서는 버킷 이름에 계정 번호를 직접 썼다. 이번 방식이 공개 저장소에 더 나은 이유는?

<details>
<summary>답</summary>

코드에 계정 번호가 없다. 실행할 때 로그인한 계정에서 읽어 오므로, 같은 코드를 다른 계정에서 실행해도 그 계정 번호로 이름이 만들어진다. 다만 `backend` 블록에는 변수를 쓸 수 없다(실습 6).

</details>

<details>
<summary>정답 코드</summary>

`variables.tf`

```hcl
variable "env" {
  description = "환경 이름"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["prod", "dev"], var.env)
    error_message = "env는 prod 또는 dev만 쓸 수 있다."
  }
}

variable "stack" {
  description = "Stack 태그 값"
  type        = string
  default     = "practice"
}

variable "purpose" {
  description = "버킷 용도. 버킷 이름 가운데에 들어간다"
  type        = string
}
```

`main.tf` (`terraform` 블록은 공통 코드 그대로)

```hcl
provider "aws" {
  region = "ap-northeast-2"
  default_tags {
    tags = { Project = "fitjob", Env = var.env, ManagedBy = "terraform", Stack = var.stack }
  }
}

data "aws_caller_identity" "current" {}

locals {
  name_prefix = "fitjob-practice"
  bucket_name = "${local.name_prefix}-${var.purpose}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "this" {
  bucket = local.bucket_name
}
```

`outputs.tf`

```hcl
output "bucket_name" {
  value = aws_s3_bucket.this.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.this.arn
}

output "account_id" {
  value = data.aws_caller_identity.current.account_id
}
```

`terraform.tfvars`

```hcl
purpose = "vars"
```

</details>

**참고 메모** (실습하면서 나온 질문)

<details>
<summary><code>variables.tf</code>는 값을 모아 두는 곳인가? Terraform이 정한 파일 이름인가?</summary>

**값이 아니라 "입력 목록"을 적는 곳이다.** 어떤 변수가 있는지(이름, 타입, 설명, 기본값, 검사 규칙)를 적는다. 함수로 치면 매개변수 목록이다. 실제로 넣을 값은 보통 `terraform.tfvars`에 따로 적는다. 이 실습에서 `purpose`의 선언은 `variables.tf`에, 값 `"vars"`는 `terraform.tfvars`에 둔 것이 그 예다. 이렇게 나누면 코드는 그대로 두고 `tfvars`만 바꿔 다른 값으로 실행할 수 있다.

**`variables.tf`라는 이름은 관례다.** Terraform은 폴더 안의 `*.tf`를 이름과 상관없이 전부 하나로 합쳐 읽는다. `variable` 블록을 `main.tf`에 써도 같이 동작한다. 그래도 `main.tf` / `variables.tf` / `outputs.tf`로 나누는 건 처음 보는 사람도 어디에 뭐가 있는지 바로 찾게 하려는 것이다.

반대로 Terraform이 이름을 보고 다르게 다루는 파일도 있다.

| 파일 | 하는 일 |
|---|---|
| `terraform.tfvars` | 이 이름이면 변수 값을 **자동으로** 읽는다 |
| `*.auto.tfvars` | 이것도 자동으로 읽는다 |
| 그 밖의 `.tfvars` (예: `dev.tfvars`) | 자동으로 읽지 않는다. `-var-file=dev.tfvars`로 직접 넘긴다 |
| `terraform.tfstate` | 로컬 state 파일. Terraform이 만들고 관리한다 |
| `.terraform.lock.hcl` | 프로바이더 버전 고정. `init`이 만든다 |
| `.terraform/` | 내려받은 프로바이더와 모듈이 들어가는 폴더 |

`variables.tf`는 이름을 바꿔도 되고, `terraform.tfvars`는 이름이 바뀌면 자동으로 읽히지 않는다.

</details>

<details>
<summary><code>variables.tf</code>를 바꾸면 <code>var.env</code>의 <code>var</code>도 바뀌나?</summary>

바뀌지 않는다. `var`는 Terraform이 정해 둔 **고정된 접두어**다. 파일 이름이나 파일 내용에서 오는 게 아니다.

```text
var . env
 ↑     ↑
 고정   variable "env" { ... } 의 이름(내가 정한다)
```

| `variables.tf`에서 바꾼 것 | `main.tf`에 생기는 일 |
|---|---|
| `default = "prod"` → `"dev"` (값) | 코드는 그대로. `var.env`의 값만 `"dev"`가 된다 |
| `variable "env"` → `variable "environment"` (이름) | `var.env`를 전부 `var.environment`로 직접 고쳐야 한다. 안 고치면 `validate`에서 `Reference to undeclared input variable` 오류 |
| 파일 이름 `variables.tf` → `inputs.tf` | 아무 일도 없다 |

접두어는 종류마다 정해져 있다.

| 쓰는 모양 | 가리키는 것 |
|---|---|
| `var.이름` | `variable` 블록 |
| `local.이름` | `locals` 블록 안의 값. 블록은 `locals`, 참조는 `local.`(s 없음)이라 헷갈리기 쉽다 |
| `data.종류.이름` | `data` 블록 |
| `module.이름` | `module` 블록 (실습 10) |
| `종류.이름` (접두어 없음) | `resource` 블록. 예: `aws_s3_bucket.this` |

</details>

<details>
<summary>리소스는 <code>aws_s3_bucket.this</code>인데 왜 data는 <code>data.</code>를 붙여야 하나?</summary>

**리소스와 데이터 소스가 같은 종류 이름을 쓸 수 있어서**, 둘을 구분하려고 붙인다. 예를 들어 `aws_s3_bucket`은 리소스로도, 데이터 소스로도 있다.

```hcl
# 버킷을 만든다
resource "aws_s3_bucket" "this" {
  bucket = "fitjob-practice-first-<계정ID>"
}

# 이미 있는 다른 버킷을 읽기만 한다
data "aws_s3_bucket" "this" {
  bucket = "some-existing-bucket"
}
```

종류도 이름도 같다. 접두어가 없으면 `aws_s3_bucket.this.arn`이 어느 쪽인지 알 수 없다.

- `aws_s3_bucket.this.arn` → 내가 **만든** 버킷
- `data.aws_s3_bucket.this.arn` → **읽어 온** 버킷

리소스가 가장 많이 쓰이니 짧게 쓰게 하고, 나머지(`var.`, `local.`, `data.`, `module.`)에 접두어를 붙인 설계다. `aws_caller_identity`처럼 데이터 소스로만 있는 종류도 규칙을 맞추려고 항상 `data.`를 붙인다.

</details>

### 실습 4. count와 for_each

| 항목 | 내용 |
|---|---|
| 목표 | 같은 리소스를 여러 개 만드는 두 방법을 비교하고, 하나를 뺄 때 무슨 일이 생기는지 본다 |
| 폴더 | `04-count-foreach/` |
| 리소스 | SSM 파라미터 스토어의 표준 파라미터(무료). 실제로 `storage` 스택이 앱 설정을, `database` 스택이 DB 주소(`/fitjob/prod/db/endpoint`)를 여기에 둔다 |

**새 개념**

| 방법 | 쓰는 법 | 주소 모양 | 구별하는 기준 |
|---|---|---|---|
| `count = 3` | `count.index`(0, 1, 2) | `aws_ssm_parameter.by_count[0]` | **순서 번호** |
| `for_each = toset([...])` 또는 맵 | `each.key`, `each.value` | `aws_ssm_parameter.by_each["alpha"]` | **이름(키)** |

**과제.** 변수 `names`(기본값 `["alpha", "beta", "gamma"]`)로 파라미터를 두 벌 만든다.

1. `count`로: 이름 `/fitjob-practice/count/<이름>`, 값은 이름 그대로
2. `for_each`로: 이름 `/fitjob-practice/each/<이름>`, 값은 이름 그대로
3. 두 벌의 파라미터 이름 목록을 output으로

**실행**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 1 | `terraform apply` | `6 added` | |
| 2 | `terraform state list` | `by_count[0]`~`[2]`, `by_each["alpha"]` 등 | 주소 모양 |
| 3 | `terraform state show 'aws_ssm_parameter.by_each["beta"]'` | 파라미터 설정 | 주소에 `"`와 `[`가 있으면 셸이 해석하지 않게 작은따옴표로 감싼다 |
| 4 | `names`에서 `"alpha"`를 빼고 `terraform plan` (**apply하지 않는다**) | count 쪽은 `[0]`·`[1]` 교체(`-/+`)와 `[2]` 삭제. for_each 쪽은 `["alpha"]`만 삭제. `2 to add, 0 to change, 4 to destroy` | count는 번호가 하나씩 당겨진다 |
| 5 | `"alpha"`를 다시 넣고 `terraform plan` | `No changes.` | |
| 6 | `terraform destroy` | `6 destroyed` | |

**생각해 볼 질문.** 서브넷 6개를 `count`로 만들었는데 첫 번째 서브넷이 필요 없어졌다. 빼면 어떻게 될까? `count`는 언제 쓰면 좋을까?

<details>
<summary>답</summary>

- 나머지 5개가 번호가 하나씩 당겨져 모두 교체 대상이 된다. 그 안에 EC2나 RDS가 있으면 서브넷을 지울 수 없어 apply가 멈추거나, 안의 리소스까지 다시 만들어야 한다. 그래서 실습 5는 `public-2a`처럼 이름을 키로 쓰는 `for_each`를 쓴다.
- `count`는 "켜기·끄기" 스위치에 알맞다. 예: `count = var.enable_db_access ? 1 : 0`. Phase 2의 DB 접속용 임시 EC2처럼 잠깐 있다가 없어지는 리소스다.

</details>

<details>
<summary>정답 코드 (공통 코드 아래)</summary>

```hcl
variable "names" {
  type    = list(string)
  default = ["alpha", "beta", "gamma"]
}

resource "aws_ssm_parameter" "by_count" {
  count = length(var.names)
  name  = "/fitjob-practice/count/${var.names[count.index]}"
  type  = "String"
  value = var.names[count.index]
}

resource "aws_ssm_parameter" "by_each" {
  for_each = toset(var.names)
  name     = "/fitjob-practice/each/${each.key}"
  type     = "String"
  value    = each.value
}

output "count_names" {
  value = aws_ssm_parameter.by_count[*].name
}

output "each_names" {
  value = [for p in aws_ssm_parameter.by_each : p.name]
}
```

</details>

**참고 메모** (실습하면서 나온 질문)

<details>
<summary><code>aws_ssm_parameter</code>는 무엇인가?</summary>

AWS Systems Manager의 **파라미터 스토어(Parameter Store)에 값 하나를 저장하는 리소스**다. 파라미터 스토어는 AWS 안의 설정값 저장소다. 이름과 값을 한 쌍으로 저장하고, 이름은 폴더 경로처럼 붙인다. 앱이나 서버는 실행할 때 이름으로 값을 꺼내 간다. 그래서 DB 주소 같은 값을 코드나 서버에 박아 두지 않아도 된다.

| 이름 | 값 |
|---|---|
| `/fitjob/prod/db/endpoint` | `fitjob-db.xxxx.ap-northeast-2.rds.amazonaws.com` |
| `/fitjob-practice/each/alpha` | `alpha` |

| 인자 | 뜻 |
|---|---|
| `name` | 경로 모양의 이름 |
| `type` | `String`(일반 문자열), `StringList`(쉼표로 이은 목록), `SecureString`(암호화 저장. 비밀번호·API 키용) |
| `value` | 저장할 값 |

- 이 실습에서 쓰는 이유: 표준(Standard) 파라미터는 만들어 두기만 해서는 무료라 마음껏 만들었다 지울 수 있다. 진짜 프로젝트에서도 `database` 스택이 DB 주소를 `/fitjob/prod/db/endpoint`에 넣고 앱이 거기서 읽는다(실습 7의 답).
- 확인: 콘솔 **Systems Manager → 파라미터 스토어**, 또는 `aws ssm get-parameter --name /fitjob-practice/each/alpha --query Parameter.Value --output text`
- 실습 11에서는 반대로 `data "aws_ssm_parameter"`로, AWS가 공개해 둔 최신 AMI ID를 읽기만 한다.

</details>

<details>
<summary><code>count</code> 쪽은 무엇을 만들고, <code>count.index</code>는 무엇인가?</summary>

`count.index`는 **지금 몇 번째를 만드는 중인지 나타내는 번호**다. `count = 3`이면 블록을 3번 찍어 내고, 매번 0, 1, 2를 차례로 넣는다(0부터 시작). `var.`처럼 Terraform이 정해 둔 이름이고, `count`를 쓴 블록 안에서만 쓸 수 있다.

| `count.index` | `var.names[count.index]` | `name` | 주소 |
|---|---|---|---|
| 0 | `"alpha"` | `/fitjob-practice/count/alpha` | `by_count[0]` |
| 1 | `"beta"` | `/fitjob-practice/count/beta` | `by_count[1]` |
| 2 | `"gamma"` | `/fitjob-practice/count/gamma` | `by_count[2]` |

- 이름 구분자는 `.`이 아니라 `/`다.
- `length(var.names)`: 목록의 길이(3). `names`에 하나를 더 넣으면 자동으로 4개가 된다.
- `var.names[count.index]`: 목록에서 그 번호의 값을 꺼낸다. `${...}`는 문자열 안에 값을 끼워 넣는다.
- Terraform은 이것들을 **번호**로 구분한다. 그래서 4번에서 `"alpha"`를 빼면 `beta`가 `[0]`, `gamma`가 `[1]`로 당겨지고, 각 번호의 `name`이 바뀌니 교체가 일어난다.

</details>

<details>
<summary><code>for_each</code> 쪽에서 <code>each.key</code>와 <code>each.value</code>는 어떻게 들어가나?</summary>

`for_each`는 받은 모음의 **원소마다** 블록을 하나씩 찍어 내고, 그때마다 `each.key`와 `each.value`에 그 원소의 값을 넣는다.

**`toset(var.names)`: 목록을 집합으로 바꾼다.** `for_each`는 목록을 직접 받지 않고 집합이나 맵만 받는다. 목록은 순서(번호)로 구분하는데, `for_each`는 이름으로 구분하려는 것이라서다. 집합이 되면 중복이 사라지고 순서는 의미가 없어진다.

**집합일 때는 key = value = 원소다.** 집합에는 키가 따로 없어서 원소 자체를 둘 다로 쓴다. 그래서 `value = each.key`로 써도 결과가 같다.

| `each.key` | `each.value` | `name` | 주소 |
|---|---|---|---|
| `"alpha"` | `"alpha"` | `/fitjob-practice/each/alpha` | `by_each["alpha"]` |
| `"beta"` | `"beta"` | `/fitjob-practice/each/beta` | `by_each["beta"]` |
| `"gamma"` | `"gamma"` | `/fitjob-practice/each/gamma` | `by_each["gamma"]` |

**맵을 넘기면 key와 value가 다르다.** 맵의 키가 `each.key`, 값이 `each.value`다.

```hcl
resource "aws_ssm_parameter" "by_map" {
  for_each = {
    alpha = "first"
    beta  = "second"
  }
  name  = "/fitjob-practice/map/${each.key}"   # alpha, beta
  type  = "String"
  value = each.value                           # first, second
}
```

실습 5의 서브넷이 이 방식이다. 키는 `"public-2a"` 같은 이름, 값은 `{ cidr, az, tier }` 묶음이라 `each.value.cidr`처럼 안의 값을 꺼낸다.

| | `count` | `for_each` |
|---|---|---|
| 받는 것 | 숫자 | 집합 또는 맵 |
| 블록 안에서 쓰는 것 | `count.index` (0, 1, 2) | `each.key`, `each.value` |
| 주소 | `by_count[0]` | `by_each["alpha"]` |
| 하나를 빼면 | 뒤 번호가 당겨져 교체된다 | 뺀 것만 지워진다 |

</details>

### 기초 연습 문제

실습 1~4를 따라 했어도 빈 파일 앞에서는 막힐 수 있다. 정답 코드를 읽고 이해하는 것과 스스로 쓰는 것은 다른 기술이다. 아래 5문제는 실습 1~4의 개념을 다른 리소스와 다른 모양으로 다시 쓰게 한다. 모두 무료 리소스다.

**푸는 순서** (모든 문제에 똑같이 쓴다)

| 단계 | 할 일 | 막히면 |
|---|---|---|
| 1 | 과제 문장에서 "무엇을 만드나"를 찾아 리소스 종류를 정한다 | Registry에서 키워드로 찾는다([1.6](#16-aws-프로바이더와-registry-문서)) |
| 2 | 그 리소스 문서의 Example Usage를 복사한다 | |
| 3 | Argument Reference에서 `Required`를 채우고, 과제에 나온 설정에 맞는 `Optional`을 찾는다 | |
| 4 | 같은 문자열을 두 번 쓰거나 다른 리소스의 값을 쓰는 곳은 참조·`var.`·`local.`로 바꾼다 | 실습 3 참고 메모의 접두어 표 |
| 5 | `fmt` → `validate` → **요약 줄을 먼저 예상해 적고** `plan` | 예상과 다르면 왜 다른지 찾는다. 그게 공부다 |

- 힌트와 정답은 접어 두었다. 10분 넘게 막히면 힌트 1, 그래도 막히면 힌트 2, 마지막에 정답을 연다.
- 폴더는 문제마다 만든다(`d1-log-group/` 등). 이전 실습 폴더의 lock 파일을 복사한 뒤 `init`하면 프로바이더를 다시 내려받지 않는다([Q14](qa-log.md#q14-terraformrc에-캐시-폴더를-설정하고-terraform-init을-했는데-프로바이더가-캐시에-저장됐는지-어떻게-확인해)). 예: 새 폴더에서 `cp ../04-count-foreach/.terraform.lock.hcl .`
- 공통 코드([1.3](#13-공통-코드))는 모든 문제의 `main.tf` 맨 위에 둔다. 문제 2·4는 `Env = "prod"`를 `Env = var.env`로 바꾼다.
- 정답 코드는 Terraform 1.17.1·AWS 프로바이더 6.74.0에서 `fmt -check`·`validate`를 통과했다. 처음 plan 개수와 표에 적은 오류 메시지도 실제 출력으로 확인했다(2026-11-28, 리소스는 만들지 않음).

| # | 문제 | 다시 쓰는 개념 | 관련 실습 | 시간 |
|---|---|---|---|---|
| 1 | [처음 보는 리소스 쓰기](#문제-1-처음-보는-리소스-쓰기) | Registry 읽기, 참조, `~`와 `-/+` | 1, 1.6 | 30분 |
| 2 | [plan 결과 미리 맞히기](#문제-2-plan-결과-미리-맞히기) | count·for_each 주소, `default_tags` | 3, 4 | 30분 |
| 3 | [오류 메시지 읽고 고치기](#문제-3-오류-메시지-읽고-고치기) | 접두어, 블록 문법, `${}` | 3 | 20분 |
| 4 | [맵으로 앱 설정 넣기](#문제-4-맵으로-앱-설정-넣기) | `map` 변수, 맵 `for_each`, `for` 식 output | 3, 4 | 40분 |
| 5 | [스위치로 켜고 끄기](#문제-5-스위치로-켜고-끄기) | `bool` 변수, `count = 조건 ? 1 : 0`, `[0]` | 3, 4 | 30분 |

### 문제 1. 처음 보는 리소스 쓰기

| 항목 | 내용 |
|---|---|
| 목표 | 한 번도 안 써 본 리소스를 문서만 보고 쓴다. 고쳐지는 변경(`~`)과 교체되는 변경(`-/+`)을 구별한다 |
| 폴더 | `d1-log-group/` |
| 리소스 | CloudWatch 로그 그룹. 로그를 넣지 않으면 무료다. 실제로 `storage` 스택이 API 로그 그룹 `/fitjob/prod/api`(보존 30일)를 만든다([인프라 명세 9장](../05-infrastructure.md#9-관측알림)) |

**과제.** 공통 코드 아래에 다음 2개를 쓴다. 라벨(리소스 이름)은 `api`, `log_group_arn`으로 한다.

1. CloudWatch 로그 그룹 `/fitjob-practice/api`. 로그는 7일 동안 보관한다.
2. SSM 파라미터 `/fitjob-practice/log-group-arn`. 값은 1번 로그 그룹의 ARN이고, `type`은 `String`이다.

조건: ARN을 문자열로 적지 않는다.

<details>
<summary>힌트 1</summary>

- Registry에서 `cloudwatch log group`으로 찾는다. 리소스 종류는 `aws_cloudwatch_log_group`이고, 문서 주소 끝은 `resources/cloudwatch_log_group`이다.
- "7일 보관"에 맞는 인자를 Argument Reference에서 찾는다. 이름에 `retention`이 들어 있다.

</details>

<details>
<summary>힌트 2</summary>

- 로그 그룹 이름은 `name`, 보관 기간은 `retention_in_days`다.
- ARN은 Attribute Reference의 `arn`이다. 참조 모양은 `종류.라벨.속성`이다.
- SSM 파라미터는 실습 4에서 쓴 `aws_ssm_parameter`다.

</details>

**실행**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 1 | 요약 줄을 예상해 적고 `terraform plan` | `Plan: 2 to add`. 로그 그룹 `arn`은 `(known after apply)`, 파라미터 `value`는 `(sensitive value)` | `value`는 문서에 "plan에서 항상 민감 값으로 표시한다"고 적혀 있다. 그래서 아직 모르는 값도 가려서 보여 준다 |
| 2 | `retention_in_days = 10`으로 바꾸고 `terraform validate` | `expected retention_in_days to be one of [0 1 3 5 7 14 30 ...], got 10` | 허용값이 정해진 인자는 AWS에 묻기 전에 걸린다. 허용값 목록은 문서의 인자 설명에 있다 |
| 3 | 7로 되돌리고 `terraform apply` | 로그 그룹이 `Creation complete`된 뒤 파라미터가 만들어진다 | 참조가 순서를 만든다 |
| 4 | `terraform console`에서 `aws_cloudwatch_log_group.api.arn`을 입력하고 `exit` | `arn:aws:logs:ap-northeast-2:<계정 번호>:log-group:/fitjob-practice/api` | 만든 뒤의 값은 console로 본다 |
| 5 | `retention_in_days`를 14로 바꾸고, 예상한 뒤 `plan` → `apply` | 로그 그룹만 `~ update in-place`. `0 to add, 1 to change, 0 to destroy` | `Forces new resource`가 없는 인자는 고쳐진다 |
| 6 | 이름을 `/fitjob-practice/web`으로 바꾸고, 예상한 뒤 `plan` (**apply하지 않는다**) | 로그 그룹 `-/+`와 `# forces replacement`, 파라미터 `~`. `1 to add, 1 to change, 1 to destroy` | 아래 질문 |
| 7 | 이름을 되돌리고 `terraform destroy` | `2 destroyed` | |

**생각해 볼 질문.** 실습 1의 6번에서는 버킷 이름을 바꾸자 딸린 설정 2개도 교체(`-/+`)됐다. 이번 6번에서는 파라미터가 교체되지 않고 `~`다. 무엇이 다를까?

<details>
<summary>답</summary>

딸린 리소스가 교체되는지는 **딸린 리소스 쪽에서 바뀌는 인자**가 `Forces new resource`인지에 달려 있다.

| | 딸린 리소스에서 바뀌는 인자 | 교체 대상인가 | 결과 |
|---|---|---|---|
| 실습 1의 6번 | 퍼블릭 접근 차단·버전 관리의 `bucket` | 예. 다른 버킷을 가리키게 된다 | `-/+` |
| 문제 1의 6번 | 파라미터의 `value` | 아니오 | `~` |

문서에 표시가 없어도 교체될 수 있다. `aws_ssm_parameter`의 `name`은 문서 인자 줄에 `Forces new resource`가 없다. 하지만 프로바이더 소스에는 교체 대상(`ForceNew`)으로 되어 있다(2026-11-28, 6.74.0 소스 확인). 실습 4의 4번에서 count 쪽이 교체된 이유다. 그래서 최종 판단은 plan의 `# forces replacement`로 한다.

</details>

<details>
<summary>정답 코드 (공통 코드 아래)</summary>

```hcl
resource "aws_cloudwatch_log_group" "api" {
  name              = "/fitjob-practice/api"
  retention_in_days = 7
}

resource "aws_ssm_parameter" "log_group_arn" {
  name  = "/fitjob-practice/log-group-arn"
  type  = "String"
  value = aws_cloudwatch_log_group.api.arn
}
```

</details>

### 문제 2. plan 결과 미리 맞히기

| 항목 | 내용 |
|---|---|
| 목표 | 코드를 바꾸기 전에 plan 결과를 맞힌다. apply 전에 plan을 읽는 눈을 기른다 |
| 폴더 | `d2-predict/` |

**준비.** 공통 코드의 `Env = "prod"`를 `Env = var.env`로 바꾸고, 그 아래에 다음 코드를 붙인다. `terraform apply` → `6 added`.

```hcl
variable "env" {
  type    = string
  default = "prod"
}

variable "names" {
  type    = list(string)
  default = ["red", "green", "blue"]
}

resource "aws_ssm_parameter" "by_count" {
  count = length(var.names)
  name  = "/fitjob-practice/predict/count/${var.names[count.index]}"
  type  = "String"
  value = var.names[count.index]
}

resource "aws_ssm_parameter" "by_each" {
  for_each = toset(var.names)
  name     = "/fitjob-practice/predict/each/${each.key}"
  type     = "String"
  value    = each.value
}
```

**과제.** 아래 변경마다 세 가지를 한다.

1. 코드를 고치기 전에 요약 줄(`N to add, N to change, N to destroy`)과 바뀌는 주소를 적는다.
2. 고친 뒤 `terraform plan`으로 맞춰 본다.
3. **apply하지 않고** 원래대로 되돌린다. 매번 준비 상태(6개)에서 시작한다.

| # | 변경 | 내 예상 |
|---|---|---|
| A | `names` 끝에 `"black"`을 추가한다 → `["red", "green", "blue", "black"]` | |
| B | 가운데 `"green"`을 뺀다 → `["red", "blue"]` | |
| C | 순서만 바꾼다 → `["blue", "green", "red"]` | |
| D | 코드는 그대로 두고 `terraform plan -var 'env=dev'` | |
| E | `by_each`의 라벨을 `by_key`로 바꾼다 (`resource "aws_ssm_parameter" "by_key"`) | |

끝나면 `terraform destroy` → `6 destroyed`.

<details>
<summary>힌트</summary>

- count는 번호로, for_each는 키로 구별한다. count는 번호마다 "전에는 어떤 이름이었고, 지금은 어떤 이름인가"를 표로 그려 본다.
- SSM 파라미터의 `name`이 바뀌면 교체(`-/+`)다. 교체 1개는 add 1개와 destroy 1개로 센다. `value`나 태그만 바뀌면 `~`다.
- Terraform은 리소스를 **주소**로 기억한다. 주소가 바뀌면 같은 리소스로 보지 않는다.

</details>

<details>
<summary>답</summary>

| # | 요약 줄 | 바뀌는 주소 | 이유 |
|---|---|---|---|
| A | `2 to add, 0 to change, 0 to destroy` | `by_count[3]`, `by_each["black"]` 추가 | 끝에 붙이면 기존 번호는 그대로다 |
| B | `1 to add, 0 to change, 3 to destroy` | `by_count[1]` 교체(green → blue), `by_count[2]` 삭제, `by_each["green"]` 삭제 | count는 뒤의 번호가 하나씩 당겨진다 |
| C | `2 to add, 0 to change, 2 to destroy` | `by_count[0]`(red → blue)과 `by_count[2]`(blue → red) 교체. for_each 쪽은 그대로 | `toset`은 순서가 없는 집합이라 순서를 바꿔도 같다 |
| D | `0 to add, 6 to change, 0 to destroy` | 6개 모두 `~`. `tags_all`의 `Env`만 `"prod" -> "dev"` | `default_tags`는 모든 리소스에 붙는다(실습 3의 6번) |
| E | `3 to add, 0 to change, 3 to destroy` | `by_each[...]` 3개 삭제, `by_key[...]` 3개 생성 | 라벨이 바뀌면 주소가 바뀐다. 옛 주소는 지우고 새 주소는 만든다. 같은 SSM 이름을 지우면서 만들므로 apply가 실패할 수도 있다. 라벨만 바꾸려면 `moved` 블록을 쓴다(실습 9) |

</details>

### 문제 3. 오류 메시지 읽고 고치기

| 항목 | 내용 |
|---|---|
| 목표 | 오류 메시지에서 위치와 원인을 읽고 고친다. `validate`가 못 잡는 실수는 plan에서 찾는다 |
| 폴더 | `d3-fix-errors/` |

**과제.** 아래 코드를 공통 코드 아래에 붙인다. 실수가 6개 있다.

1. `terraform validate`를 실행하고, 나온 오류를 하나씩 고친다. 고칠 때마다 아래 표에 적는다.
2. `Success!`가 나오면 `terraform plan`을 읽고 마지막 실수를 찾는다. apply는 하지 않는다.

```hcl
variable "purpose" {
  type    = string
  default = "errors"
}

data "aws_caller_identity" "current" {}

locals {
  bucket_name = "fitjob-practice-var.purpose-${aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "this" {
  name = locals.bucket_name
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration = {
    status = "Enabled"
  }
}

output "bucket_arn" {
  value = aws_s3_bucket.this.arn
}

output "env" {
  value = var.env
}
```

| 차례 | 오류 제목 (`Error:` 뒤) | 문제가 된 코드 | 원인 | 고친 코드 |
|---|---|---|---|---|
| | | | | |

**오류 읽는 순서**

| 순서 | 볼 곳 | 예 |
|---|---|---|
| 1 | `Error:` 뒤 제목 | `Unsupported argument` |
| 2 | `on main.tf line N` 아래의 코드 줄 | 어느 줄인지. 줄 번호는 내 공통 코드 모양에 따라 다르다 |
| 3 | 마지막 설명 | `Did you mean ...?`이 답을 알려 줄 때가 많다 |

<details>
<summary>힌트</summary>

- 오류는 한 번에 다 나오지 않는다. 앞의 오류를 고쳐야 다음 검사로 넘어갈 때가 있다. 처음에는 3개가 나온다.
- 실습 3 참고 메모의 접두어 표와 Registry의 `aws_s3_bucket`·`aws_s3_bucket_versioning` 인자를 다시 본다.
- 마지막 실수는 plan의 `bucket = "..."` 줄에 보인다. 버킷 이름이 생각한 모양인지 본다.

</details>

<details>
<summary>답</summary>

| 차례 | 오류 제목 | 문제가 된 코드 | 원인 | 고친 코드 |
|---|---|---|---|---|
| 1회 | `Reference to undeclared resource` | `${aws_caller_identity.current.account_id}` | `data.` 접두어가 빠졌다. 오류 끝에 `Did you mean the data resource data.aws_caller_identity.current?`라고 나온다 | `${data.aws_caller_identity.current.account_id}` |
| 1회 | `Unsupported argument` | `name = locals.bucket_name` | 버킷 이름 인자는 `bucket`이다(`An argument named "name" is not expected here.`) | `bucket = ...` |
| 1회 | `Reference to undeclared input variable` | `value = var.env` | `variable "env"` 선언이 없다 | `variable "env"` 블록을 추가한다(기본값 `"prod"`). 필요 없는 output이면 지워도 된다 |
| 2회 | `Reference to undeclared resource` | `locals.bucket_name` | 참조는 `local.`(s 없음)이다. 접두어가 없는 이름은 리소스 종류로 읽어서 `A managed resource "locals" "bucket_name" has not been declared`라고 나온다 | `local.bucket_name` |
| 3회 | `Unsupported argument`와 `Insufficient versioning_configuration blocks` | `versioning_configuration = {` | 중괄호 블록에는 `=`를 쓰지 않는다. 실수 하나에서 오류 2개가 나왔다(`Did you mean to define a block of type "versioning_configuration"?`) | `versioning_configuration {` |
| plan | 오류 없음 | plan의 `bucket = "fitjob-practice-var.purpose-<계정 번호>"` | 문자열 안에서 `${}` 없이 쓴 `var.purpose`는 그냥 글자다 | `"fitjob-practice-${var.purpose}-${...}"` |

`validate`는 문법과 이름만 검사한다. 값이 의도대로인지는 plan을 읽어야 안다.

</details>

<details>
<summary>정답 코드 (공통 코드 아래)</summary>

```hcl
variable "purpose" {
  type    = string
  default = "errors"
}

variable "env" {
  type    = string
  default = "prod"
}

data "aws_caller_identity" "current" {}

locals {
  bucket_name = "fitjob-practice-${var.purpose}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "this" {
  bucket = local.bucket_name
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = "Enabled"
  }
}

output "bucket_arn" {
  value = aws_s3_bucket.this.arn
}

output "env" {
  value = var.env
}
```

</details>

### 문제 4. 맵으로 앱 설정 넣기

| 항목 | 내용 |
|---|---|
| 목표 | 설정 여러 개를 맵 변수 하나로 받아 SSM 파라미터로 만든다 |
| 폴더 | `d4-app-settings/` |
| 이어지는 실제 작업 | `storage` 스택이 앱 설정을 `/fitjob/prod/app/reasons_mode` 같은 SSM 파라미터로 둔다([인프라 명세 6장](../05-infrastructure.md#6-비밀정보와-설정)) |

**새 개념**

| 개념 | 뜻 |
|---|---|
| `map(string)` | 키와 값의 짝을 모은 것. `{ log_level = "info", page_size = "20" }` |
| 맵으로 `for_each` | `each.key`는 키, `each.value`는 값이다. 실습 4의 `toset`은 키와 값이 같았다 |
| `{ for k, v in ... : k => v }` | 맵을 만드는 `for` 식이다. 리스트는 `[for ...]`, 맵은 `{for ...}` |

**과제**

1. `variables.tf`: `env`(실습 3과 같다. 기본값 `prod`, `prod`·`dev`만 허용), `app_settings`(`map(string)`, 기본값 `reasons_mode = "llm"`, `log_level = "info"`, `page_size = "20"`)
2. `main.tf`: 공통 코드의 `Env`를 `var.env`로 바꾼다. `locals`에 접두어 `/fitjob-practice/<env>/app`을 만든다. `app_settings` 항목마다 SSM 파라미터를 하나씩 만든다. 이름은 `<접두어>/<키>`, 값은 맵의 값이다
3. `outputs.tf`: `param_names`(파라미터 이름 리스트), `param_arns`(키 → ARN 맵)
4. `dev.tfvars`: `env = "dev"`, `app_settings = { reasons_mode = "template" }` (일부러 하나만 적는다)

<details>
<summary>힌트 1</summary>

- `for_each = var.app_settings`처럼 맵을 그대로 넘긴다. `toset()`은 필요 없다.
- 파라미터 이름은 `"${local.접두어이름}/${each.key}"` 모양이다.

</details>

<details>
<summary>힌트 2</summary>

- `param_names`는 실습 4의 `each_names`와 같은 모양이다: `[for p in aws_ssm_parameter.app : p.name]`
- `param_arns`는 `{ for k, p in aws_ssm_parameter.app : k => p.arn }`이다. for_each 리소스를 `for`로 돌면 `k`에 키, `p`에 리소스 하나가 들어온다.

</details>

**실행**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 1 | `terraform plan` | `3 to add`. 주소가 `aws_ssm_parameter.app["log_level"]`처럼 키로 나온다 | |
| 2 | `terraform apply` | `Outputs:`에 `param_arns`(키 3개)와 `param_names`(이름 3개) | |
| 3 | `terraform console`에서 `local.<접두어 이름>`, `keys(var.app_settings)`를 입력하고 `exit` | `"/fitjob-practice/prod/app"`, `tolist(["log_level", "page_size", "reasons_mode"])` | `keys`는 키를 알파벳순 리스트로 준다 |
| 4 | `variables.tf`에서 `log_level` 기본값을 `"warn"`으로 바꾸고, 예상한 뒤 `plan`. 끝나면 되돌린다 | `0 to add, 1 to change, 0 to destroy`. `app["log_level"]`만 `~` | 키가 그대로면 값만 고쳐진다 |
| 5 | 예상한 뒤 `terraform plan -var-file=dev.tfvars` (**apply하지 않는다**) | `1 to add, 0 to change, 3 to destroy` | 아래 질문 |
| 6 | `terraform destroy` | `3 destroyed` | |

**생각해 볼 질문.** 5번에서 `dev.tfvars`에는 `reasons_mode`만 적었다. `log_level`·`page_size`는 기본값이 쓰일 것 같은데 왜 삭제될까? `reasons_mode`는 왜 교체될까?

<details>
<summary>답</summary>

1. 맵 변수에 값을 넘기면 기본값과 **합쳐지지 않고 통째로 바뀐다.** `dev.tfvars`의 `app_settings`는 키가 1개인 맵이다. 그래서 `log_level`·`page_size` 키가 사라지고 그 파라미터 2개가 삭제된다.
2. `env`가 `dev`가 되어 접두어가 `/fitjob-practice/dev/app`으로 바뀐다. `app["reasons_mode"]`는 `name`이 바뀌므로 교체(`-/+`)다.
3. 합계는 add 1(교체), destroy 3(교체 1 + 삭제 2)이다.

기본값에 일부만 덮어쓰고 싶으면 변수를 둘로 나누고 `merge(기본 맵, 덮어쓸 맵)` 함수로 합친다.

</details>

<details>
<summary>정답 코드</summary>

`variables.tf`

```hcl
variable "env" {
  description = "환경 이름"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["prod", "dev"], var.env)
    error_message = "env는 prod 또는 dev만 쓸 수 있다."
  }
}

variable "app_settings" {
  description = "앱 설정. 키는 파라미터 이름 끝, 값은 파라미터 값이 된다"
  type        = map(string)
  default = {
    reasons_mode = "llm"
    log_level    = "info"
    page_size    = "20"
  }
}
```

`main.tf` (공통 코드의 `Env`를 `var.env`로 바꾼 아래)

```hcl
locals {
  param_prefix = "/fitjob-practice/${var.env}/app"
}

resource "aws_ssm_parameter" "app" {
  for_each = var.app_settings
  name     = "${local.param_prefix}/${each.key}"
  type     = "String"
  value    = each.value
}
```

`outputs.tf`

```hcl
output "param_names" {
  value = [for p in aws_ssm_parameter.app : p.name]
}

output "param_arns" {
  value = { for k, p in aws_ssm_parameter.app : k => p.arn }
}
```

`dev.tfvars`

```hcl
env = "dev"
app_settings = {
  reasons_mode = "template"
}
```

</details>

### 문제 5. 스위치로 켜고 끄기

| 항목 | 내용 |
|---|---|
| 목표 | 변수 하나로 리소스를 만들거나 없앤다. count가 붙은 리소스를 `[0]`으로 참조한다 |
| 폴더 | `d5-switch/` |
| 이어지는 실제 작업 | 잠깐 있다 없어지는 리소스. 예: Phase 2의 DB 접속용 임시 EC2([인프라 명세 8.5](../05-infrastructure.md#85-db-접속용-임시-ec2-phase-2)) |

**새 개념**

| 개념 | 뜻 |
|---|---|
| `bool` | `true` 또는 `false` 둘 중 하나인 타입 |
| `조건 ? 참일 때 값 : 거짓일 때 값` | 조건식. `count = var.enable_archive ? 1 : 0`이면 켜면 1개, 끄면 0개다 |
| `aws_s3_bucket.archive[0]` | count가 붙으면 리소스가 목록이 된다. 하나뿐이어도 `[0]`을 붙여 꺼낸다 |
| `null` | "값 없음" |

**과제.** 아래 요구사항만 보고 처음부터 쓴다.

> 보관용 버킷은 필요할 때만 만든다. 변수 `enable_archive`(기본값 `false`)가 `true`일 때만 버킷 `fitjob-practice-archive-<계정 번호>`를 만들고, 퍼블릭 접근 차단 4개를 켠다. 계정 번호는 코드에 적지 않는다. 버킷 이름을 output `archive_bucket`으로 내보내고, 버킷이 없으면 `null`로 한다.

<details>
<summary>힌트 1</summary>

- 계정 번호는 실습 3처럼 `data "aws_caller_identity"`와 `locals`로 만든다.
- 버킷과 퍼블릭 접근 차단 모두에 `count = var.enable_archive ? 1 : 0`을 쓴다.

</details>

<details>
<summary>힌트 2</summary>

- 퍼블릭 접근 차단의 `bucket`은 `aws_s3_bucket.archive[0].id`다. `[0]`을 빼면 `Missing resource instance key` 오류가 난다. 오류 설명은 `Because aws_s3_bucket.archive has "count" set, its attributes must be accessed on specific instances.`다.
- output은 `var.enable_archive ? aws_s3_bucket.archive[0].bucket : null`이다.

</details>

**실행**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 1 | `terraform plan` | `No changes.` | 기본값이 `false`라 만들 것이 없다 |
| 2 | 예상한 뒤 `terraform plan -var 'enable_archive=true'` | `2 to add`. 주소에 `[0]`이 붙는다(`aws_s3_bucket.archive[0]`) | |
| 3 | `terraform apply -var 'enable_archive=true'` | `2 added`. `Outputs:`에 `archive_bucket` | |
| 4 | 예상한 뒤 `-var` 없이 `terraform plan` | `0 to add, 0 to change, 2 to destroy` | `-var`는 기억되지 않는다. Terraform은 매번 코드와 그때 받은 값으로 비교한다 |
| 5 | `-var` 없이 `terraform apply` → 요약 줄을 확인하고 `yes` | `2 destroyed` | 스위치를 끄면 지워진다 |

**생각해 볼 질문.** 실제 스택에서 `-var 'enable_archive=true'`를 매번 손으로 넣으면 어떤 사고가 날 수 있을까? 어떻게 막을까?

<details>
<summary>답</summary>

- 한 번 빼먹으면 4번처럼 지우려고 한다. 데이터가 든 버킷이면 사고다(빈 버킷이 아니면 `BucketNotEmpty`로 멈추지만, `force_destroy = true`였다면 지워진다).
- 켜 둘 값은 `terraform.tfvars`에 적는다. 그러면 plan마다 같은 값이 들어간다.
- 지우면 안 되는 리소스에는 `prevent_destroy`를 붙인다(실습 6).

</details>

<details>
<summary>정답 코드 (공통 코드 아래)</summary>

```hcl
variable "enable_archive" {
  description = "true일 때만 보관용 버킷을 만든다"
  type        = bool
  default     = false
}

data "aws_caller_identity" "current" {}

locals {
  archive_bucket_name = "fitjob-practice-archive-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "archive" {
  count  = var.enable_archive ? 1 : 0
  bucket = local.archive_bucket_name
}

resource "aws_s3_bucket_public_access_block" "archive" {
  count                   = var.enable_archive ? 1 : 0
  bucket                  = aws_s3_bucket.archive[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "archive_bucket" {
  value = var.enable_archive ? aws_s3_bucket.archive[0].bucket : null
}
```

</details>

---

## 3. Phase 1 예행연습 (실습 5~11)

### 실습 5. 미니 network 스택

| 항목 | 내용 |
|---|---|
| 목표 | [인프라 명세 2장](../05-infrastructure.md#2-네트워크)·[3장](../05-infrastructure.md#3-보안-그룹)의 네트워크를 대역만 바꿔 코드로 만든다 |
| 폴더 | `05-network/` (실습 7·10·11에서 계속 쓴다. 지우지 않는다) |
| 비용 | 0. VPC, 서브넷, 라우팅 테이블, IGW, S3 게이트웨이 엔드포인트, 보안 그룹은 모두 무료다 |

**과제.** 아래를 만든다.

| 리소스 | 이름(`Name` 태그) | 설정 |
|---|---|---|
| VPC | `fitjob-practice-vpc` | `10.1.0.0/16`, DNS 확인·호스트 이름 켬 |
| 서브넷 6개 | `fitjob-practice-public-2a` 등 | public `10.1.1.0/24`(2a)·`10.1.2.0/24`(2c), app `10.1.11.0/24`·`10.1.12.0/24`, db `10.1.21.0/24`·`10.1.22.0/24` |
| 인터넷 게이트웨이 | `fitjob-practice-igw` | |
| 라우팅 테이블 3개 | `fitjob-practice-rt-public`, `-rt-app`, `-rt-db` | 각 계층의 서브넷 2개를 연결 |
| 경로 1개 | | `rt-public`의 `0.0.0.0/0` → IGW |
| S3 게이트웨이 엔드포인트 | `fitjob-practice-s3-endpoint` | `rt-app`에 연결 |
| 보안 그룹 2개 | `fitjob-practice-sg-alb`, `-sg-app` | `sg-alb`: 443 ← 0.0.0.0/0, 8000 → `sg-app`. `sg-app`: 8000 ← `sg-alb`, 443 → 0.0.0.0/0 |
| output | | VPC ID, 서브넷 ID 맵, 라우팅 테이블 ID 맵, IGW ID, 보안 그룹 ID 맵 |

**힌트**

| 힌트 | 이유 |
|---|---|
| 서브넷은 `locals`에 `"public-2a" = { cidr, az, tier }` 모양의 맵으로 적고 `for_each` | 실습 4. `tier`가 있으면 어느 라우팅 테이블에 연결할지 찾을 수 있다 |
| 라우팅 테이블도 `for_each = toset(["public", "app", "db"])` | |
| 기본 경로는 `aws_route`로 따로 만들고, `aws_route_table` 안에 `route` 블록을 쓰지 않는다 | 실습 7에서 이유를 본다([인프라 명세 2.2](../05-infrastructure.md#22-라우팅-테이블)) |
| 보안 그룹 규칙은 `aws_vpc_security_group_ingress_rule`·`_egress_rule`로 규칙마다 하나씩 만든다 | 보안 그룹 안의 `ingress {}` 블록과 섞으면 서로 덮어쓴다 |
| Terraform으로 만든 보안 그룹은 콘솔과 달리 "아웃바운드 전체 허용" 기본 규칙이 지워진다 | 필요한 아웃바운드는 직접 적는다 |
| 보안 그룹 설명(description)은 영어로 쓴다 | 한글을 받지 않는다 |
| 실제 `sg-alb`는 CloudFront 접두사 목록에서만 받는다 | 연습은 0.0.0.0/0으로 줄였다 |

**실행** (WSL 터미널, `05-network/`에서)

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 1 | `terraform init` → `terraform plan` | `Plan: 25 to add` | |
| 2 | `terraform apply` | 1~2분 | |
| 3 | VPC 콘솔 → `fitjob-practice-vpc` → 리소스 맵 | 서브넷 6개, 라우팅 테이블, IGW, 엔드포인트가 선으로 이어진 그림 | |
| 4 | `aws ec2 describe-route-tables --filters Name=vpc-id,Values=$(terraform output -raw vpc_id) --query 'length(RouteTables)'` | `4` | 3개는 우리 것, 1개는 VPC를 만들 때 AWS가 자동으로 만든 기본(main) 라우팅 테이블이다. state에 없다 |
| 5 | `aws ec2 describe-security-groups --filters Name=vpc-id,Values=$(terraform output -raw vpc_id) --query 'SecurityGroups[].GroupName'` | `default`를 포함해 3개 | 기본 보안 그룹도 자동으로 생긴다([인프라 명세 13.2](../05-infrastructure.md#132-콘솔-단계-규칙)의 `aws_default_*`) |
| 6 | `terraform plan` | `No changes.` | |

**생각해 볼 질문**

1. 지금 app 서브넷에 EC2를 두면 인터넷으로 나갈 수 있을까?
2. `sg-alb` 안에 `egress { security_groups = [sg-app] }`를, `sg-app` 안에 `ingress { security_groups = [sg-alb] }`를 인라인으로 쓰면 어떻게 될까?

<details>
<summary>답</summary>

1. 나갈 수 없다. `rt-app`에는 VPC 내부 경로(local)와 S3 엔드포인트 경로만 있고 `0.0.0.0/0`이 없다. 그 경로를 `nat` 스택이 켤 때 넣고 끌 때 뺀다.
2. 순환 참조(`Cycle`) 오류가 난다. 서로가 먼저 있어야 만들 수 있어서다. 규칙을 따로 된 리소스로 두면 보안 그룹 2개를 먼저 만들고 규칙을 나중에 만들 수 있다.

</details>

<details>
<summary>정답 코드 (공통 코드 아래)</summary>

```hcl
locals {
  name = "fitjob-practice"
  subnets = {
    "public-2a" = { cidr = "10.1.1.0/24", az = "ap-northeast-2a", tier = "public" }
    "public-2c" = { cidr = "10.1.2.0/24", az = "ap-northeast-2c", tier = "public" }
    "app-2a"    = { cidr = "10.1.11.0/24", az = "ap-northeast-2a", tier = "app" }
    "app-2c"    = { cidr = "10.1.12.0/24", az = "ap-northeast-2c", tier = "app" }
    "db-2a"     = { cidr = "10.1.21.0/24", az = "ap-northeast-2a", tier = "db" }
    "db-2c"     = { cidr = "10.1.22.0/24", az = "ap-northeast-2c", tier = "db" }
  }
  tiers = toset(["public", "app", "db"])
}

resource "aws_vpc" "main" {
  cidr_block           = "10.1.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${local.name}-vpc" }
}

resource "aws_subnet" "this" {
  for_each          = local.subnets
  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az
  tags              = { Name = "${local.name}-${each.key}" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name}-igw" }
}

resource "aws_route_table" "this" {
  for_each = local.tiers
  vpc_id   = aws_vpc.main.id
  tags     = { Name = "${local.name}-rt-${each.key}" }
}

resource "aws_route" "public_default" {
  route_table_id         = aws_route_table.this["public"].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "this" {
  for_each       = local.subnets
  subnet_id      = aws_subnet.this[each.key].id
  route_table_id = aws_route_table.this[each.value.tier].id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.ap-northeast-2.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.this["app"].id]
  tags              = { Name = "${local.name}-s3-endpoint" }
}

resource "aws_security_group" "alb" {
  name        = "${local.name}-sg-alb"
  description = "practice ALB"
  vpc_id      = aws_vpc.main.id
}

resource "aws_security_group" "app" {
  name        = "${local.name}-sg-app"
  description = "practice app server"
  vpc_id      = aws_vpc.main.id
}

resource "aws_vpc_security_group_ingress_rule" "alb_https_in" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "alb_to_app" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}

resource "aws_vpc_security_group_egress_rule" "app_https_out" {
  security_group_id = aws_security_group.app.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "subnet_ids" {
  value = { for k, s in aws_subnet.this : k => s.id }
}

output "route_table_ids" {
  value = { for k, rt in aws_route_table.this : k => rt.id }
}

output "igw_id" {
  value = aws_internet_gateway.main.id
}

output "sg_ids" {
  value = { alb = aws_security_group.alb.id, app = aws_security_group.app.id }
}
```

</details>

### 실습 6. state를 S3로 옮기기

| 항목 | 내용 |
|---|---|
| 목표 | `bootstrap` 스택의 순서를 그대로 연습한다. 콘솔로 만든 state 버킷을 로컬 state로 가져온 뒤, state를 그 버킷으로 옮긴다([인프라 명세 10.1](../05-infrastructure.md#101-저장소-배치)) |
| 폴더 | `06-state-bucket/` (실습 12까지 지우지 않는다. 실습 7~11의 state가 이 버킷에 들어간다) |

**새 개념**

| 개념 | 뜻 |
|---|---|
| backend | state를 둘 곳. 없으면 폴더의 `terraform.tfstate`(로컬). `backend "s3"`면 S3 객체 |
| `use_lockfile = true` | 실행하는 동안 S3에 `.tflock` 파일을 만들어, 두 곳에서 동시에 실행하지 못하게 막는다 |
| `terraform init -migrate-state` | backend를 바꾼 뒤 기존 state를 새 곳으로 복사한다 |
| `lifecycle { prevent_destroy = true }` | 이 리소스를 지우는 plan이 나오면 오류로 멈춘다. state 버킷, RDS처럼 잃으면 큰일인 것에 쓴다 |

**① 콘솔 구축.** S3 콘솔에서 버킷을 만든다.

| 설정 | 값 |
|---|---|
| 이름 | `fitjob-practice-tfstate-<계정ID>` |
| 리전 | 서울 |
| 퍼블릭 액세스 차단 | 모두 차단(기본값) |
| 버전 관리 | **활성화** (state가 망가지면 이전 버전으로 되돌린다) |
| 기본 암호화 | SSE-S3(기본값) |
| 태그 | `Project=fitjob`, `Env=prod`, `Stack=practice`, `ManagedBy=console` |

**② 가져오기 (로컬 state).** 아직 `backend` 블록 없이 쓴다.

과제: `import` 블록 4개와 `resource` 블록 4개를 **직접** 쓴다(이번에는 `-generate-config-out` 없이). 대상은 버킷, 버전 관리, 퍼블릭 접근 차단, 기본 암호화(`aws_s3_bucket_server_side_encryption_configuration`)다. import ID는 Registry 문서 맨 아래 "Import" 절에 있다([1.6](#16-aws-프로바이더와-registry-문서)). 넷 다 버킷 이름이다. 버킷에는 `prevent_destroy`를 단다.

| # | 할 일 | 기대 결과 |
|---|---|---|
| 1 | `terraform init` → `terraform plan` | `4 to import`. 태그 때문에 `1 to change`(`ManagedBy` `console` → `terraform`) |
| 2 | 암호화 설정에 `bucket_key_enabled` 차이가 나오면 콘솔 값(`true`)을 코드에 적고 다시 plan | 이것이 ③ "차이 맞추기"다 |
| 3 | `terraform apply` → `terraform plan` | `No changes.` |
| 4 | `import` 블록 4개를 지운다 | 끝난 import 블록은 지워도 된다 |

**③ state 옮기기.** `terraform` 블록 안에 `backend "s3"`를 추가한다(아래 정답 코드).

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 5 | `terraform init -migrate-state` | "Do you want to copy existing state to the new backend?" → `yes` | |
| 6 | `terraform state list` | 4개 그대로 | 이제 S3에서 읽는다 |
| 7 | S3 콘솔에서 버킷 열기 | `practice/state-bucket/terraform.tfstate` 객체 | 버킷 자신의 장부가 그 버킷 안에 있다 |
| 8 | 터미널 A에서 `terraform apply`를 실행하고 `Enter a value:`에서 멈춰 둔다. 터미널 B에서 `terraform plan` | B에 `Error acquiring the state lock`. S3 콘솔에 `.tflock` 객체 | 잠금. 내가 apply하는 중에 nightly-down이 돌아도 막힌다 |
| 9 | 터미널 A에 `no` | 잠금이 풀리고 `.tflock`이 사라진다 | |
| 10 | `terraform plan -destroy` | `Instance cannot be destroyed` 오류 | `prevent_destroy`. 실제 destroy 없이 plan으로만 확인한다 |

**생각해 볼 질문**

1. backend 블록의 `bucket`에 `"fitjob-practice-tfstate-${data.aws_caller_identity.current.account_id}"`처럼 쓸 수 있을까?
2. 진짜 `bootstrap` 스택은 왜 destroy 후 apply로 재현 확인을 하지 않을까([인프라 명세 13.3](../05-infrastructure.md#133-스택별-진행))?

<details>
<summary>답</summary>

1. 쓸 수 없다. backend는 `init` 때 다른 무엇보다 먼저 읽혀서 변수·data·locals를 쓸 수 없다. 공개 저장소에 계정 번호를 두기 싫으면 backend 블록을 비워 두고 `terraform init -backend-config=backend.hcl`처럼 값만 저장소 밖 파일로 넘기는 방법(부분 설정)이 있다. 진짜 스택에서 어떻게 할지는 Phase 1에서 정한다.
2. state 버킷을 지우면 그 안의 모든 스택 장부가 함께 사라진다. 자기 장부가 자기 안에 있어서, 지우는 순간 지운 기록도 남길 곳이 없다.

</details>

<details>
<summary>정답 코드</summary>

```hcl
terraform {
  required_version = ">= 1.11"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }

  # ③에서 추가한다
  backend "s3" {
    bucket       = "fitjob-practice-tfstate-<계정ID>"
    key          = "practice/state-bucket/terraform.tfstate"
    region       = "ap-northeast-2"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = "ap-northeast-2"
  default_tags {
    tags = { Project = "fitjob", Env = "prod", ManagedBy = "terraform", Stack = "practice" }
  }
}

# ②에서 쓰고, apply한 뒤 지운다
import {
  to = aws_s3_bucket.tfstate
  id = "fitjob-practice-tfstate-<계정ID>"
}

import {
  to = aws_s3_bucket_versioning.tfstate
  id = "fitjob-practice-tfstate-<계정ID>"
}

import {
  to = aws_s3_bucket_public_access_block.tfstate
  id = "fitjob-practice-tfstate-<계정ID>"
}

import {
  to = aws_s3_bucket_server_side_encryption_configuration.tfstate
  id = "fitjob-practice-tfstate-<계정ID>"
}

resource "aws_s3_bucket" "tfstate" {
  bucket = "fitjob-practice-tfstate-<계정ID>"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true # plan에 차이가 나올 때만 적는다
  }
}
```

</details>

### 실습 7. 스택 나누기

| 항목 | 내용 |
|---|---|
| 목표 | 상시 스택(`network`)과 온디맨드 스택(`nat`)의 관계를 연습한다. 온디맨드 스택이 상시 스택의 output을 읽고, 상시 스택의 라우팅 테이블에 경로를 넣었다 뺐다 한다 |
| 폴더 | `05-network/`(상시 역할), `07-ondemand/`(온디맨드 역할) |

**새 개념**

| 개념 | 뜻 |
|---|---|
| `data "terraform_remote_state"` | 다른 스택의 state에서 **output만** 읽는다. 진짜 스택에서 `nat`가 `network`의 라우팅 테이블 ID를 이렇게 읽는다([인프라 명세 10.2](../05-infrastructure.md#102-스택-구성과-적용-순서)) |
| 참조 방향 | 온디맨드 → 상시만 된다. 상시 스택은 온디맨드 스택을 읽지 않는다 |

**과제**

1. `05-network/`에 backend 블록을 추가한다. `key = "practice/network/terraform.tfstate"`. `terraform init -migrate-state`로 옮긴다
2. `07-ondemand/`를 만든다. backend `key = "practice/ondemand/terraform.tfstate"`. `terraform_remote_state`로 network를 읽고, `rt-app`에 `0.0.0.0/0` → IGW 경로(`aws_route`) 하나를 만든다

진짜 `nat` 스택에서는 이 경로가 NAT 인스턴스의 ENI로 간다. 연습에서는 무료인 IGW로 대신한다. 퍼블릭 IP가 없는 인스턴스에게는 IGW 경로가 쓸모없으니 모양만 연습하는 것이다.

**실행**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 1 | `05-network/`: backend 추가 → `terraform init -migrate-state` → `yes` | S3에 `practice/network/terraform.tfstate` | |
| 2 | `07-ondemand/`: `terraform init` → `terraform plan` | `1 to add` | output을 읽어 온다 |
| 3 | `terraform apply` | `1 added`. VPC 콘솔에서 `rt-app`에 `0.0.0.0/0` 경로가 생김 | |
| 4 | `05-network/`: `terraform plan` | `No changes.` | network는 자기가 만들지 않은 경로를 건드리지 않는다 |
| 5 | `05-network/`: `aws_route_table`에 `route = []`를 한 줄 넣고 `terraform plan` (**apply하지 않는다**) | `rt-app`(과 `rt-public`)의 `0.0.0.0/0` 경로를 지우겠다는 `~` | 라우팅 테이블이 경로 목록을 직접 쥐면, network를 apply할 때마다 nat가 넣은 경로를 지운다. 그래서 인라인 `route`를 쓰지 않는다 |
| 6 | 그 줄을 지우고 `terraform plan` | `No changes.` | |
| 7 | `07-ondemand/`: `terraform destroy` | `1 destroyed`. 경로만 사라짐 | `make down`이 하는 일. network는 그대로다 |
| 8 | `05-network/`: `terraform plan` | `No changes.` | |

**생각해 볼 질문.** 반대로 network가 `terraform_remote_state`로 ondemand의 output을 읽는다면, ondemand를 끈 날 network는 어떻게 될까? DB 주소는 왜 SSM 파라미터로 넘길까?

<details>
<summary>답</summary>

ondemand를 끄면 그 state에 output이 없어서, network의 plan이 `Unsupported attribute` 같은 오류로 멈춘다. 상시 스택이 온디맨드 스택에 묶여 버린다. 그래서 온디맨드 스택이 만든 값 중 다른 곳에 필요한 것(DB 주소)은 Terraform이 읽지 않고, 앱이 실행할 때 SSM 파라미터 `/fitjob/prod/db/endpoint`에서 읽는다(CLAUDE.md 설계 원칙).

</details>

<details>
<summary>정답 코드</summary>

`05-network/main.tf`의 `terraform` 블록 안에 추가

```hcl
  backend "s3" {
    bucket       = "fitjob-practice-tfstate-<계정ID>"
    key          = "practice/network/terraform.tfstate"
    region       = "ap-northeast-2"
    encrypt      = true
    use_lockfile = true
  }
```

`07-ondemand/main.tf` (`provider` 블록은 공통 코드 그대로)

```hcl
terraform {
  required_version = ">= 1.11"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  backend "s3" {
    bucket       = "fitjob-practice-tfstate-<계정ID>"
    key          = "practice/ondemand/terraform.tfstate"
    region       = "ap-northeast-2"
    encrypt      = true
    use_lockfile = true
  }
}

data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "fitjob-practice-tfstate-<계정ID>"
    key    = "practice/network/terraform.tfstate"
    region = "ap-northeast-2"
  }
}

# 진짜 nat 스택에서는 NAT 인스턴스 ENI로 가는 경로다
resource "aws_route" "app_default" {
  route_table_id         = data.terraform_remote_state.network.outputs.route_table_ids["app"]
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = data.terraform_remote_state.network.outputs.igw_id
}
```

</details>

### 실습 8. 콘솔 VPC 가져오기와 재현

| 항목 | 내용 |
|---|---|
| 목표 | Phase 1 `network`의 ①~④를 작게 해 본다. 콘솔로 만든 리소스 6개를 한 번에 가져와 초안을 정리하고, 지운 뒤 코드만으로 다시 만든다([인프라 명세 13.1](../05-infrastructure.md#131-절차)) |
| 폴더 | `08-console-vpc/` (실습 9에서 계속 쓴다) |

**① 콘솔 구축.** VPC 콘솔에서 하나씩 만든다. **"VPC 등" 마법사를 쓰지 않는다**(NAT Gateway가 생길 수 있다). 모든 리소스에 태그 `Project=fitjob`, `Env=prod`, `Stack=practice`, `ManagedBy=console`을 붙이고, 만들 때마다 ID를 메모한다.

| 순서 | 만들 것 | 설정 |
|---|---|---|
| 1 | VPC | "VPC만", 이름 `fitjob-practice-console-vpc`, `10.2.0.0/16`. 만든 뒤 "VPC 설정 편집"에서 DNS 호스트 이름 켜기 |
| 2 | 서브넷 | `fitjob-practice-console-public-2a`, `10.2.1.0/24`, `ap-northeast-2a` |
| 3 | 인터넷 게이트웨이 | `fitjob-practice-console-igw`, 만든 뒤 VPC에 연결 |
| 4 | 라우팅 테이블 | `fitjob-practice-console-rt-public`. 라우팅 편집에서 `0.0.0.0/0` → IGW, 서브넷 연결 편집에서 2번 서브넷 |

**② 코드 작성·import**

| # | 할 일 | 기대 결과 |
|---|---|---|
| 1 | 공통 코드와 `import` 블록 6개를 쓴다(아래 표) | |
| 2 | `terraform init` → `terraform plan -generate-config-out=generated.tf` | `generated.tf`가 생긴다. `conflicts with` 오류가 나도 파일은 만들어진다 |
| 3 | 초안을 아래 표대로 정리해 `main.tf`로 옮기고 `generated.tf`를 지운다 | |

| `to` | `id` 모양 |
|---|---|
| `aws_vpc.main` | `vpc-0abc...` |
| `aws_subnet.public_2a` | `subnet-0abc...` |
| `aws_internet_gateway.main` | `igw-0abc...` |
| `aws_route_table.public` | `rtb-0abc...` |
| `aws_route.public_default` | `rtb-0abc..._0.0.0.0/0` (라우팅 테이블 ID, 밑줄, 목적지) |
| `aws_route_table_association.public_2a` | `subnet-0abc.../rtb-0abc...` (서브넷 ID, 슬래시, 라우팅 테이블 ID) |

**초안 정리**

| 초안 내용 | 처리 | 이유 |
|---|---|---|
| `vpc_id = "vpc-0abc..."`처럼 ID가 문자열로 박혀 있다 | `aws_vpc.main.id` 같은 참조로 바꾼다 | **가장 중요하다.** ④에서 다시 만들면 ID가 바뀐다. 참조여야 만드는 순서도 생긴다 |
| `aws_route_table` 안의 `route`(경로 목록) | 지운다 | 경로는 `aws_route`로 따로 관리한다. 둘 다 있으면 서로 덮어쓴다(실습 7) |
| `availability_zone`과 `availability_zone_id`가 함께 있다 | `availability_zone_id`를 지운다 | 함께 쓸 수 없는 인자라 `conflicts with` 오류가 난다 |
| `tags_all` | 지운다 | 계산값이다 |
| `null`인 인자, 기본값과 같은 인자(`instance_tenancy = "default"`, `map_public_ip_on_launch = false`, `ipv6_` 로 시작하는 것 등) | 지운다 | 짧게. 남겨도 동작은 같다 |
| `tags`의 `ManagedBy = "console"` | 지운다 | `default_tags`의 `terraform`으로 바꾼다. `Name`은 남긴다 |

**③ 차이 맞추기**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 4 | `terraform plan` | `6 to import`. 태그가 있는 4개(VPC, 서브넷, IGW, 라우팅 테이블)는 `to change` | |
| 5 | `terraform apply` → `terraform plan` | `No changes.` | ③ 완료 기준 |
| 6 | `aws resourcegroupstaggingapi get-resources --tag-filters Key=ManagedBy,Values=console --query 'ResourceTagMappingList[].ResourceARN'` | 이번 리소스는 목록에 없다(실습 2를 아직 안 했다면 그 버킷만 나온다) | Phase 1 완료 기준 "`ManagedBy=console` 0개"를 확인하는 법 |

**④ 재현 확인**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 7 | `terraform output vpc_id`로 지금 ID를 적어 둔다(정답 코드처럼 output을 추가) | `vpc-...` | |
| 8 | `terraform destroy` | `6 destroyed`. 콘솔에서 VPC가 사라짐 | |
| 9 | `import` 블록을 그대로 둔 채 `terraform plan` | `Cannot import non-existent remote object` 오류 | 지운 리소스의 ID를 가리키는 import 블록은 재현을 막는다 |
| 10 | `import` 블록을 모두 지우고 `terraform apply` | `6 added` | 코드만으로 다시 만들었다 |
| 11 | `terraform output vpc_id` | 7번과 **다른** ID | ID는 재현할 때마다 바뀐다. 다른 스택이 ID를 문자열로 갖고 있으면 안 되는 이유 |
| 12 | 콘솔 리소스 맵에서 1번 때와 모양 비교 | 같은 모양 | |

<details>
<summary>정답 코드 (정리가 끝난 모습, 공통 코드 아래)</summary>

```hcl
resource "aws_vpc" "main" {
  cidr_block           = "10.2.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "fitjob-practice-console-vpc" }
}

resource "aws_subnet" "public_2a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.2.1.0/24"
  availability_zone = "ap-northeast-2a"
  tags              = { Name = "fitjob-practice-console-public-2a" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "fitjob-practice-console-igw" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "fitjob-practice-console-rt-public" }
}

resource "aws_route" "public_default" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public_2a" {
  subnet_id      = aws_subnet.public_2a.id
  route_table_id = aws_route_table.public.id
}

output "vpc_id" {
  value = aws_vpc.main.id
}
```

</details>

### 실습 9. 드리프트와 state 다루기

| 항목 | 내용 |
|---|---|
| 목표 | 콘솔 변경이 어떻게 드러나고 되돌려지는지 보고, 리소스를 지우지 않고 장부만 고치는 법을 익힌다 |
| 폴더 | `08-console-vpc/` |

**새 개념**

| 명령·블록 | 하는 일 | 실물을 바꾸나 |
|---|---|---|
| `terraform plan -detailed-exitcode` | 끝난 뒤 숫자로 결과를 알린다. 0 = 차이 없음, 1 = 오류, 2 = 차이 있음. 매일 드리프트 점검이 이 숫자를 본다([인프라 명세 10.4](../05-infrastructure.md#104-코드-품질)) | 아니요 |
| `terraform plan -refresh-only` | 장부를 실물에 맞추면 무엇이 바뀌는지 보여 준다. 일반 plan은 반대로 실물을 코드에 맞춘다 | 아니요 |
| `moved { from, to }` | 코드 안의 이름(주소)만 바꾼다. 리소스는 그대로 | 아니요 |
| `removed { from, lifecycle { destroy = false } }` | 장부에서만 뺀다. 실물은 남는다. 다른 스택으로 옮길 때 쓴다 | 아니요 |
| `terraform state rm <주소>` | `removed`와 같은 일을 plan 없이 바로 한다 | 아니요. 검토 단계가 없어 `removed`를 더 권한다 |

**A. 드리프트**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 1 | VPC 콘솔에서 `fitjob-practice-console-vpc`에 태그 `Test = drift` 추가 | | |
| 2 | `terraform plan -detailed-exitcode; echo $?` | `~ tags`에 `- "Test" = "drift"`, 마지막에 `2` | 콘솔 변경을 지우겠다고 나온다 |
| 3 | `terraform plan -refresh-only` | "Objects have changed outside of Terraform" | 장부만 고치는 제안. 코드는 그대로라 그 뒤 일반 plan은 여전히 태그를 지우려 한다 |
| 4 | `terraform apply` → `terraform plan -detailed-exitcode; echo $?` | 태그가 지워지고 `0` | 콘솔 변경은 다음 apply가 되돌린다. 남기고 싶으면 코드에 적는다 |
| 5 | 콘솔에서 VPC 설정 편집 → DNS 호스트 이름 끄기 → `terraform plan` | `~ enable_dns_hostnames = false -> true` | 태그보다 위험한 드리프트. 가져온 뒤 콘솔 수정 금지인 이유 |
| 6 | `terraform apply` | 다시 켜진다 | |

**B. 이름만 바꾸기 (`moved`)**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 7 | `aws_vpc.main`을 `aws_vpc.this`로 바꾸고(참조하는 곳과 output도) `terraform plan` (**apply하지 않는다**) | `aws_vpc.main` 삭제, `aws_vpc.this` 생성, 서브넷·라우팅 테이블도 `-/+` | 주소가 바뀌면 Terraform은 다른 리소스로 본다 |
| 8 | `moved` 블록을 추가하고 `terraform plan` | `has moved to`, `0 to add, 0 to change, 0 to destroy` | |
| 9 | `terraform apply` | 장부의 주소만 바뀐다 | |

**C. 장부에서만 빼기 (`removed`)**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 10 | `aws_route_table_association.public_2a` 블록을 지우고 그 자리에 `removed` 블록을 쓴 뒤 `terraform plan` | "no longer be managed" 문구, `0 to destroy` | |
| 11 | `terraform apply` → `terraform state list` | 연결이 목록에 없다. 콘솔에는 연결이 그대로 있다 | |
| 12 | `removed` 블록을 지우고, resource 블록과 import 블록(`<서브넷 ID>/<라우팅 테이블 ID>`)을 다시 쓴 뒤 `plan` → `apply` | `1 to import` → `No changes.` | 장부에서 뺀 것을 다시 가져오기. ID는 `terraform state show aws_subnet.public_2a`로 찾는다 |

<details>
<summary>정답 코드 (B·C에서 추가하는 블록)</summary>

```hcl
# B. 8번
moved {
  from = aws_vpc.main
  to   = aws_vpc.this
}

# C. 10번 (resource "aws_route_table_association" "public_2a" 블록은 지운다)
removed {
  from = aws_route_table_association.public_2a

  lifecycle {
    destroy = false
  }
}

# C. 12번 (removed 블록을 지우고 resource 블록을 되살린 뒤)
import {
  to = aws_route_table_association.public_2a
  id = "subnet-0abc.../rtb-0abc..."
}
```

</details>

### 실습 10. 모듈로 정리하기

| 항목 | 내용 |
|---|---|
| 목표 | 실습 5의 코드를 모듈로 옮긴다. 리소스는 하나도 다시 만들지 않는다 |
| 폴더 | `05-network/` 안에 `modules/network/` |
| 이어지는 실제 작업 | 진짜 저장소도 `infra/modules/network/`를 `infra/stacks/network/`가 부르는 구조다([인프라 명세 10.1](../05-infrastructure.md#101-저장소-배치)) |

**새 개념**

| 개념 | 뜻 | 비유 |
|---|---|---|
| module | 리소스 묶음을 폴더 하나로 만든 것. `variable`이 입력, `output`이 출력이다 | 함수 |
| `module "network" { source = "./modules/network" }` | 모듈 부르기. 입력 변수를 인자로 넘긴다 | 함수 호출 |
| `module.network.vpc_id` | 모듈의 output 읽기 | 반환값 |
| 모듈 안 리소스 주소 | `module.network.aws_vpc.main` | |

모듈 폴더에는 `provider`·`backend`를 쓰지 않는다. 부르는 쪽(루트)의 것을 그대로 쓴다.

**과제**

1. `modules/network/variables.tf`: `name`, `vpc_cidr`, `subnets`(맵)
2. `modules/network/main.tf`: 실습 5의 리소스를 옮기고 `local.name` 등을 변수로 바꾼다. `tiers`는 `subnets`에서 계산한다
3. `modules/network/outputs.tf`: 실습 5와 같은 output 5개
4. 루트 `main.tf`: 리소스 블록을 지우고 `module` 블록 하나와 `moved` 블록을 쓴다. 루트 output은 **이름을 그대로** 두고 값만 `module.network.…`로 바꾼다

**실행**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 1 | `moved` 없이 `terraform plan` | `Module not installed` 오류 | |
| 2 | `terraform init` → `terraform plan` (**apply하지 않는다**) | `25 to add, 25 to destroy` | 주소가 바뀌어서 전부 다시 만들려 한다 |
| 3 | `moved` 블록을 추가하고 `terraform plan` | `has moved to`만 나오고 `0 to add, 0 to change, 0 to destroy` | |
| 4 | `terraform apply` | 장부 주소만 바뀐다 | |
| 5 | `07-ondemand/`에서 `terraform plan` | 실습 7 7번 뒤라면 `1 to add`(꺼 둔 경로). 오류는 없다 | output 이름이 같으면 다른 스택은 바뀐 줄 모른다 |
| 6 | (실험) `moved` 하나(예: IGW)를 지우고 `plan` → 다시 넣기 | 그 리소스만 교체로 나온다 | 빠진 `moved`를 찾는 법 |

<details>
<summary>정답 코드</summary>

`modules/network/variables.tf`

```hcl
variable "name" {
  description = "리소스 이름 앞부분"
  type        = string
}

variable "vpc_cidr" {
  type = string
}

variable "subnets" {
  description = "서브넷 이름 => CIDR, 가용영역, 계층(public, app, db)"
  type = map(object({
    cidr = string
    az   = string
    tier = string
  }))
}
```

`modules/network/main.tf`: 실습 5 정답에서 `locals` 블록과 output을 빼고 리소스만 옮긴 뒤 아래처럼 바꾼다.

```hcl
locals {
  tiers = toset([for s in var.subnets : s.tier])
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.name}-vpc" }
}

resource "aws_subnet" "this" {
  for_each          = var.subnets
  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az
  tags              = { Name = "${var.name}-${each.key}" }
}

# 나머지 리소스: local.name → var.name, local.subnets → var.subnets 로 바꾼다
```

`modules/network/outputs.tf`: 실습 5의 output 5개를 그대로 옮긴다.

루트 `main.tf` (`terraform`·`provider` 블록 아래)

```hcl
module "network" {
  source   = "./modules/network"
  name     = "fitjob-practice"
  vpc_cidr = "10.1.0.0/16"
  subnets = {
    "public-2a" = { cidr = "10.1.1.0/24", az = "ap-northeast-2a", tier = "public" }
    "public-2c" = { cidr = "10.1.2.0/24", az = "ap-northeast-2c", tier = "public" }
    "app-2a"    = { cidr = "10.1.11.0/24", az = "ap-northeast-2a", tier = "app" }
    "app-2c"    = { cidr = "10.1.12.0/24", az = "ap-northeast-2c", tier = "app" }
    "db-2a"     = { cidr = "10.1.21.0/24", az = "ap-northeast-2a", tier = "db" }
    "db-2c"     = { cidr = "10.1.22.0/24", az = "ap-northeast-2c", tier = "db" }
  }
}

moved {
  from = aws_vpc.main
  to   = module.network.aws_vpc.main
}

moved {
  from = aws_subnet.this
  to   = module.network.aws_subnet.this
}

moved {
  from = aws_internet_gateway.main
  to   = module.network.aws_internet_gateway.main
}

moved {
  from = aws_route_table.this
  to   = module.network.aws_route_table.this
}

moved {
  from = aws_route.public_default
  to   = module.network.aws_route.public_default
}

moved {
  from = aws_route_table_association.this
  to   = module.network.aws_route_table_association.this
}

moved {
  from = aws_vpc_endpoint.s3
  to   = module.network.aws_vpc_endpoint.s3
}

moved {
  from = aws_security_group.alb
  to   = module.network.aws_security_group.alb
}

moved {
  from = aws_security_group.app
  to   = module.network.aws_security_group.app
}

moved {
  from = aws_vpc_security_group_ingress_rule.alb_https_in
  to   = module.network.aws_vpc_security_group_ingress_rule.alb_https_in
}

moved {
  from = aws_vpc_security_group_egress_rule.alb_to_app
  to   = module.network.aws_vpc_security_group_egress_rule.alb_to_app
}

moved {
  from = aws_vpc_security_group_ingress_rule.app_from_alb
  to   = module.network.aws_vpc_security_group_ingress_rule.app_from_alb
}

moved {
  from = aws_vpc_security_group_egress_rule.app_https_out
  to   = module.network.aws_vpc_security_group_egress_rule.app_https_out
}

output "vpc_id" {
  value = module.network.vpc_id
}

output "subnet_ids" {
  value = module.network.subnet_ids
}

output "route_table_ids" {
  value = module.network.route_table_ids
}

output "igw_id" {
  value = module.network.igw_id
}

output "sg_ids" {
  value = module.network.sg_ids
}
```

`for_each`로 만든 리소스(`aws_subnet.this` 등)는 `moved` 하나로 키 전부가 함께 옮겨진다.

</details>

### 실습 11. 온디맨드 EC2와 SSM 접속 (선택)

| 항목 | 내용 |
|---|---|
| 목표 | `nat`·`app` 스택에서 쓸 EC2 기본기를 익힌다. 22번 포트 없이 SSM으로 접속하고, 온디맨드 스택만 지운다 |
| 폴더 | `05-network/`(보안 그룹), `07-ondemand/`(EC2, IAM) |
| 비용 | 시간당 약 $0.011(t4g.nano $0.0052 + 퍼블릭 IPv4 $0.005 + EBS 8GB). **끝나면 바로 destroy** |

**새 개념**

| 개념 | 뜻 |
|---|---|
| `data "aws_ssm_parameter"`로 AMI 찾기 | AWS가 SSM 파라미터로 공개하는 최신 Amazon Linux 2023 AMI ID를 읽는다. AMI ID를 코드에 박지 않는다 |
| 인스턴스 프로필 | EC2에 IAM 역할을 붙이는 껍데기. 역할 → 프로필 → 인스턴스 순서로 이어진다 |
| `AmazonSSMManagedInstanceCore` | SSM 접속에 필요한 AWS 관리형 정책 |
| IMDSv2 (`http_tokens = "required"`) | 인스턴스 메타데이터를 토큰이 있어야만 읽게 한다. 보안 체크리스트 항목이다([인프라 명세 11](../05-infrastructure.md#11-보안-체크리스트)) |
| `lifecycle { ignore_changes = [ami] }` | 최신 AMI가 나와도 인스턴스를 교체하지 않는다. 없으면 AMI가 갱신될 때마다 plan에 교체가 나온다 |

**과제**

1. `05-network/` 루트(모듈 밖)에 보안 그룹 `fitjob-practice-sg-ssm-test`와 아웃바운드 443 → 0.0.0.0/0 규칙, output `ssm_test_sg_id`. 보안 그룹은 상시 스택에 둔다는 규칙을 그대로 따른다
2. `07-ondemand/`에 IAM 역할(EC2가 맡을 수 있게), 정책 연결, 인스턴스 프로필, t4g.nano 인스턴스 1대(`public-2a`, 퍼블릭 IP, IMDSv2 필수, 루트 볼륨 암호화), output `instance_id`·`public_ip`

**실행**

| # | 할 일 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 1 | `05-network/`: `terraform apply` | `2 added` | |
| 2 | `07-ondemand/`: `terraform plan` | `5 to add`(실습 7에서 지운 경로 포함) | |
| 3 | `terraform apply` | 1분 안팎 | |
| 4 | 1~2분 뒤 `aws ssm describe-instance-information --query 'InstanceInformationList[].[InstanceId,PingStatus]' --output text` | `i-... Online` | SSM 에이전트가 등록됐다 |
| 5 | `aws ssm start-session --target $(terraform output -raw instance_id)` | `sh-5.2$` 같은 셸 | 22번 포트 없이 접속 |
| 6 | (접속한 셸에서) `curl -s https://checkip.amazonaws.com` | `terraform output public_ip`와 같은 IP | Phase 1 NAT 검증과 같은 확인법 |
| 7 | (접속한 셸에서) `curl -s -o /dev/null -w '%{http_code}\n' http://169.254.169.254/latest/meta-data/instance-id` | `401` | 토큰 없는 메타데이터 요청이 막힌다(IMDSv2) |
| 8 | `exit` → `terraform destroy` | `5 destroyed` | 온디맨드 스택만 지운다 |
| 9 | `05-network/`: `terraform plan` | `No changes.` | |

**생각해 볼 질문.** 이 EC2를 `app-2a`(프라이빗)에 두면 SSM 접속이 될까? 실습 7의 `rt-app` → IGW 경로가 있으면 될까?

<details>
<summary>답</summary>

안 된다. SSM 에이전트는 인터넷의 SSM 주소로 나가야 하는데, 프라이빗 서브넷 인스턴스는 퍼블릭 IP가 없다. IGW는 퍼블릭 IP가 있는 인스턴스의 주소만 바꿔 준다. 그래서 `rt-app` → IGW 경로가 있어도 응답이 돌아오지 못한다. 프라이빗 인스턴스 대신 주소를 바꿔 주는 장치가 NAT이고, 그것이 Phase 1의 `nat` 스택이다.

</details>

<details>
<summary>정답 코드</summary>

`05-network/main.tf`에 추가

```hcl
resource "aws_security_group" "ssm_test" {
  name        = "fitjob-practice-sg-ssm-test"
  description = "practice EC2 for SSM session"
  vpc_id      = module.network.vpc_id
}

resource "aws_vpc_security_group_egress_rule" "ssm_test_https_out" {
  security_group_id = aws_security_group.ssm_test.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

output "ssm_test_sg_id" {
  value = aws_security_group.ssm_test.id
}
```

`07-ondemand/main.tf`에 추가

```hcl
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ssm_test" {
  name               = "fitjob-practice-ssm-test"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ssm_test.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ssm_test" {
  name = "fitjob-practice-ssm-test"
  role = aws_iam_role.ssm_test.name
}

data "aws_ssm_parameter" "al2023_arm64" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
}

resource "aws_instance" "ssm_test" {
  ami                         = data.aws_ssm_parameter.al2023_arm64.insecure_value
  instance_type               = "t4g.nano"
  subnet_id                   = data.terraform_remote_state.network.outputs.subnet_ids["public-2a"]
  vpc_security_group_ids      = [data.terraform_remote_state.network.outputs.ssm_test_sg_id]
  iam_instance_profile        = aws_iam_instance_profile.ssm_test.name
  associate_public_ip_address = true
  tags                        = { Name = "fitjob-practice-ssm-test" }

  metadata_options {
    http_tokens = "required"
  }

  root_block_device {
    encrypted = true
  }

  lifecycle {
    ignore_changes = [ami]
  }
}

output "instance_id" {
  value = aws_instance.ssm_test.id
}

output "public_ip" {
  value = aws_instance.ssm_test.public_ip
}
```

AMI 파라미터의 `value`는 민감값으로 표시돼 plan에 `(sensitive value)`로 나온다. AMI ID는 비밀이 아니므로 그대로 보이는 `insecure_value`를 쓴다.

</details>

---

## 4. 실습 12. 정리

`make down`처럼 **만든 순서의 반대로** 지운다. 다른 스택이 참조하는 것을 먼저 지우면 의존성 오류로 멈춘다.

| 순서 | 폴더 | 할 일 | 이유 |
|---|---|---|---|
| 1 | `07-ondemand/` | `terraform destroy` | network를 참조하는 온디맨드 스택이 먼저다 |
| 2 | `08-console-vpc/` | `terraform destroy` | |
| 3 | `05-network/` | `terraform destroy` | |
| 4 | `01`·`03`·`04` | 아직 남았으면 `terraform destroy` | |
| 5 | `02-import/` | 기초 노트 8장 13번 | |
| 6 | `06-state-bucket/` | 아래 표 | 다른 스택의 장부가 들어 있어 **맨 마지막**이다 |

state 버킷은 자기 장부를 자기 안에 두고 있어서 바로 destroy할 수 없다. 장부를 먼저 로컬로 꺼낸다.

| # | 할 일 | 기대 결과 |
|---|---|---|
| 1 | `backend "s3"` 블록을 지우고 `terraform init -migrate-state` → `yes` | 장부가 로컬 `terraform.tfstate`로 돌아온다 |
| 2 | 버킷의 `prevent_destroy`를 지우고 `force_destroy = true`를 넣은 뒤 `terraform apply` | `1 changed` |
| 3 | `terraform destroy` | `4 destroyed`. 버전 관리로 쌓인 옛 장부도 함께 지워진다 |

**남은 리소스 확인.** 모두 `[]`가 나와야 한다. 태그 검색은 지운 직후 잠시 남아 보일 수 있으니, 나오면 몇 분 뒤 다시 본다.

```bash
aws resourcegroupstaggingapi get-resources --tag-filters Key=Stack,Values=practice --query 'ResourceTagMappingList[].ResourceARN'
aws ec2 describe-vpcs --filters Name=tag:Stack,Values=practice --query 'Vpcs[].VpcId'
aws ssm get-parameters-by-path --path /fitjob-practice --recursive --query 'Parameters[].Name'
aws iam list-roles --query "Roles[?starts_with(RoleName, 'fitjob-practice')].RoleName"
```

끝나면 각 폴더의 `.terraform/`을 지워 디스크를 돌려받는다. 코드(`*.tf`)는 Phase 1에 참고하도록 남겨 둔다.

## 5. 검토 받는 법

| 언제 | 할 일 |
|---|---|
| 코드를 다 썼을 때 | 폴더 경로(예: `tf-practice/05-network`)를 알려 주면 Claude가 파일을 읽고 검토한다 |
| plan이 예상과 다를 때 | apply하지 않고 plan 결과의 마지막 30줄쯤을 붙여 넣는다 |
| 실습을 끝냈을 때 | 새로 알게 된 것이나 헷갈린 것을 물으면 [질문·답변 기록](qa-log.md)에 남긴다 |
