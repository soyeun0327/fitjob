# Terraform 기초 학습 노트

| 항목 | 내용 |
|---|---|
| 문서 버전 | v0.1 |
| 작성일 | 2026-11-10 |
| 변경 | 로드맵 Phase 0 링크 갱신(W1~3) (2026-11-24) |
| 변경 | 공개 저장소라 버킷 이름의 계정 번호를 `<계정ID>`로 바꿈 (2026-11-25) |
| 목적 | Phase 0 Terraform 기초와 S3 버킷 import 연습을 정리한다([로드맵 Phase 0](../09-roadmap.md#phase-0-준비-w13)). Phase 1부터 실제 스택을 콘솔로 만들고 가져올 때 다시 본다 |

---

## 1. Terraform이 하는 일

Terraform은 **"AWS가 이런 모습이어야 한다"를 코드로 적으면, 지금 모습과 비교해 차이만큼 AWS를 바꿔 주는 도구**다.

| 방식 | 하는 법 | 예 |
|---|---|---|
| 콘솔 | 원하는 결과까지 가는 과정을 사람이 클릭한다 | "버킷 만들기 → 이름 입력 → 태그 추가 → 저장" |
| Terraform | 원하는 결과만 적는다. 과정은 Terraform이 정한다 | "이 이름의 버킷이 있고, 태그는 이것이어야 한다" |

결과만 적는 방식을 **선언형**이라고 한다. 같은 코드를 몇 번 실행해도 결과가 같다. 이미 원하는 모습이면 아무것도 하지 않는다.

### 1.1 세 가지를 비교한다

| 요소 | 비유 | 설명 |
|---|---|---|
| 코드 (`*.tf`) | 설계도 | 원하는 모습. 사람이 쓴다 |
| state (`terraform.tfstate`) | 관리 장부 | Terraform이 자기가 관리하는 리소스와 마지막으로 본 설정을 적어 둔 파일. Terraform이 쓴다 |
| 실제 AWS | 실물 | 지금 AWS에 있는 리소스 |

- Terraform은 **state에 적힌 리소스만 자기 것으로 본다.** 콘솔로 만든 리소스는 실물은 있지만 장부에 없어서 Terraform이 모른다.
- **import**는 이미 있는 실물을 장부에 올리는 일이다. 새로 만들지 않는다.
- 콘솔에서 몰래 바꿔 코드·장부와 실물이 달라진 상태를 **드리프트**라고 한다. 다음 `plan`에서 드러난다.

### 1.2 plan과 apply

```
코드 ──┐
       ├─ plan: 셋을 비교해 "무엇을 바꿀지" 목록을 보여준다 (아무것도 바꾸지 않음)
state ─┤
       └─ apply: 그 목록대로 AWS API를 호출하고 state를 갱신한다
실물 ──┘   (plan은 시작할 때 실물을 먼저 읽어 와 장부와 맞춰 본다)
```

## 2. 기본 명령

| 명령 | 하는 일 | AWS를 바꾸나 |
|---|---|---|
| `terraform init` | 폴더를 처음 쓸 때 한 번 한다. 프로바이더(AWS와 대화하는 플러그인)를 내려받는다 | 아니요 |
| `terraform fmt` | 코드 들여쓰기와 정렬을 표준 모양으로 고친다 | 아니요 |
| `terraform validate` | 문법과 인자 이름이 맞는지 검사한다. AWS에 접속하지 않는다 | 아니요 |
| `terraform plan` | 바꿀 목록을 보여준다 | 아니요 |
| `terraform apply` | plan을 다시 보여주고, `yes`를 입력하면 실행한다 | **예** |
| `terraform destroy` | state에 있는 리소스를 **모두** 지운다. `yes`를 입력해야 실행한다 | **예** |
| `terraform state list` | 장부에 있는 리소스 주소 목록 | 아니요 |
| `terraform state show <주소>` | 장부에 적힌 그 리소스의 설정 | 아니요 |

이 프로젝트 규칙: 명령은 WSL에서 실행한다. Claude는 `apply`·`destroy`를 사용자가 요청할 때만 실행한다(CLAUDE.md "AWS 작업 규칙").

## 3. 코드 문법(HCL) 기초

Terraform 코드는 **블록**으로 이루어진다.

```hcl
블록종류 "라벨1" "라벨2" {
  인자 = 값
  안쪽블록 {
    인자 = 값
  }
}
```

| 값의 모양 | 예 |
|---|---|
| 문자열 | `"ap-northeast-2"` |
| 숫자, 참거짓 | `3`, `false` |
| 맵(키 = 값 묶음) | `{ Project = "fitjob", Env = "prod" }` |
| 주석 | `#`으로 시작하는 줄 |

이번 연습에 나오는 블록은 4종류다. `variable`(입력값), `output`(출력값), `module`(묶음 재사용)은 Phase 1에서 배운다.

| 블록 | 뜻 |
|---|---|
| `terraform { }` | Terraform 자체 설정. 버전, 쓸 프로바이더, state를 둘 곳 |
| `provider "aws" { }` | AWS에 어떻게 접속할지. 리전, 공통 태그 |
| `resource "종류" "이름" { }` | 관리할 리소스 하나의 설계도 |
| `import { }` | 이미 있는 실물을 어느 `resource`로 장부에 올릴지 |

## 4. 연습 코드 한 줄씩

```hcl
terraform {
  required_version = ">= 1.11"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}
```

| 줄 | 뜻 |
|---|---|
| `required_version = ">= 1.11"` | Terraform 1.11 이상에서만 실행된다. 설치된 버전은 1.17.1 |
| `source = "hashicorp/aws"` | AWS 프로바이더를 공식 저장소에서 받는다 |
| `version = "~> 6.0"` | 6.x 중 최신(6.0 이상 7.0 미만). 이번에 받은 것은 6.72.0 |
| (backend 없음) | state를 이 폴더의 `terraform.tfstate` 파일에 둔다(로컬 state). 실제 스택은 S3 버킷에 둔다([인프라 명세 10.3](../05-infrastructure.md#103-기본-설정)) |

```hcl
provider "aws" {
  region = "ap-northeast-2"
  default_tags {
    tags = { Project = "fitjob", Env = "prod", ManagedBy = "terraform", Stack = "practice" }
  }
}
```

| 줄 | 뜻 |
|---|---|
| `region` | 서울 리전에 접속한다. 로그인 정보는 `aws login --remote`로 받은 것을 그대로 쓴다 |
| `default_tags` | 이 프로바이더로 만드는 **모든 리소스에 자동으로 붙는 태그**. 리소스마다 태그를 적지 않아도 된다. 리소스에 같은 키를 따로 적으면 그 값이 우선한다 |

```hcl
import {
  to = aws_s3_bucket.practice
  id = "fitjob-prod-import-practice-<계정ID>"
}
```

| 줄 | 뜻 |
|---|---|
| `to` | 장부에서 쓸 주소. 아래 `resource` 블록과 이어진다 |
| `id` | AWS에 있는 실물의 ID. S3 버킷은 버킷 이름이 ID다(VPC라면 `vpc-0abc...`) |

`<계정ID>`는 12자리 AWS 계정 번호로 바꿔 쓴다. 공개 저장소라 문서에는 적지 않는다. 실제 값은 `aws sts get-caller-identity --query Account --output text`로 확인한다.

```hcl
resource "aws_s3_bucket" "practice" {
  bucket = "fitjob-prod-import-practice-<계정ID>"
  tags   = { ManagedBy = "console" }
}
```

| 줄 | 뜻 |
|---|---|
| `"aws_s3_bucket"` | 리소스 종류. 앞의 `aws_`가 AWS 프로바이더 것이라는 뜻이다 |
| `"practice"` | **코드 안에서만 쓰는 이름**. AWS 버킷 이름과는 다르다. 종류와 합친 `aws_s3_bucket.practice`가 이 리소스의 주소다 |
| `bucket` | AWS에 있는 실제 버킷 이름 |
| `tags` | 1단계에서 콘솔 값 그대로 둔다. 이 줄을 지우면 `default_tags`의 `ManagedBy = "terraform"`이 적용된다 |

## 5. 연습 폴더에 생기는 파일

| 파일 | 언제 생기나 | 뜻 | 커밋 |
|---|---|---|---|
| `main.tf` | 사람이 쓴다 | 코드 | 실제 스택이면 한다 |
| `.terraform/` | `init` | 내려받은 프로바이더 프로그램 | 안 한다 |
| `.terraform.lock.hcl` | `init` | 받은 프로바이더의 정확한 버전과 해시. 다음에 같은 버전을 쓰게 한다 | 한다 |
| `terraform.tfstate` | 첫 `apply` | 장부. 리소스 설정이 **평문**으로 들어간다 | **절대 안 한다** |
| `generated.tf.draft` | `plan -generate-config-out` | 자동으로 만든 코드 초안(아래 6.1) | 안 한다 |

state에 값이 평문으로 남기 때문에 시크릿 값은 import하지 않고, `*.tfstate`는 `.gitignore`에 있다.

## 6. import 흐름과 지금 위치

[인프라 명세 13.1](../05-infrastructure.md#131-절차)의 다섯 단계와 연습의 대응이다.

| 단계 | 연습에서 할 일 | 상태 (2026-11-10) |
|---|---|---|
| ① 콘솔 구축 | 버킷 생성, 태그 4개 | 끝 |
| ② 코드 작성·import | 코드 초안 받기 → 정리 → `apply`로 장부에 올리기 | Claude가 만든 초안과 정리 결과(4장)는 참고용으로 두고 `apply`하지 않았다. 사용자가 공부한 뒤 처음부터 직접 쓰고 Claude가 검토한다 |
| ③ 차이 맞추기 | `tags` 줄을 지우고 `apply` → `plan` "No changes" | 남음 |
| ④ 재현 확인 | (연습에서는 생략. `network` 스택부터 한다) | — |
| ⑤ 정리 | 비용 할당 태그 `Project`를 활성화한 뒤 `destroy` | 남음 |

### 6.1 코드 초안 자동 생성

`terraform plan -generate-config-out=generated.tf`는 `import` 블록이 가리키는 실물을 읽어 `resource` 블록 초안을 써 준다. 그대로 쓰지 않고 정리한다.

| 초안 내용 | 처리 | 이유 |
|---|---|---|
| `tags`에 `ManagedBy = "console"` 하나만 있다 | 1단계에서 그대로 둔다 | 나머지 3개는 `default_tags`와 값이 같아 생략됐다. 값이 다른 것만 적어 준 것이다 |
| `tags_all` | 지운다 | `default_tags`와 `tags`를 합쳐 Terraform이 계산하는 결과값이다 |
| `region`, `force_destroy`, `object_lock_enabled`, `bucket_namespace` | 지운다 | 기본값과 같다 |

## 7. plan 결과 읽는 법

| 기호·문구 | 뜻 |
|---|---|
| `will be imported` | 실물을 장부에 올린다 |
| `+` | 새로 만든다 |
| `~` | 그 자리에서 고친다 (예: 태그 변경) |
| `-` | 지운다 |
| `-/+` | 지우고 다시 만든다. 고칠 수 없는 값(예: 버킷 이름)을 바꿀 때. **데이터가 사라질 수 있어 특히 주의** |
| `Plan: 1 to import, 0 to add, 0 to change, 0 to destroy.` | 마지막 줄 요약. 여기부터 읽는다 |
| `No changes.` | 코드 = 장부 = 실물 |

## 8. 직접 해 보기

연습 폴더는 `C:\Users\soyeun\tf-practice`(WSL 경로 `/mnt/c/Users/soyeun/tf-practice`)다. Windows 편집기로 `main.tf`를 쓰고, WSL 터미널에서 이 폴더로 이동해 순서대로 실행한다. 같은 버킷을 두 폴더(두 장부)에서 import하면 안 된다. 한 리소스는 장부 하나만 관리해야 한다.

| # | 명령 | 기대 결과 | 배우는 것 |
|---|---|---|---|
| 1 | `terraform init` | "successfully initialized" | 프로바이더 내려받기 |
| 2 | `terraform state list` | 아무것도 없음 | 아직 장부가 비어 있다 |
| 3 | `terraform plan` | `1 to import, 0 to change` | import는 실물을 바꾸지 않는다 |
| 4 | `terraform apply` → `yes` | "Apply complete! Resources: 1 imported" | 장부에 올리기 |
| 5 | `terraform state list` | `aws_s3_bucket.practice` | 장부에 생겼다 |
| 6 | `terraform state show aws_s3_bucket.practice` | 버킷 설정 전체 | 장부에 무엇이 적히나 |
| 7 | `main.tf`에서 `tags = ...` 줄을 지우고 `terraform plan` | `~` 표시와 `ManagedBy = "console" -> "terraform"`, `1 to change` | 콘솔 값과 코드 값의 차이 |
| 8 | `terraform apply` → `yes` | "1 changed" | 차이를 코드 쪽으로 맞추기 |
| 9 | `terraform plan` | `No changes.` | ③ 완료 기준 |
| 10 | (선택) 콘솔에서 버킷에 태그를 하나 더 붙이고 `terraform plan` | 그 태그를 지우겠다는 `~` | 드리프트. 가져온 뒤 콘솔 수정이 금지인 이유 |
| 11 | 콘솔에서 10번 태그를 지우고 `terraform plan` | `No changes.` | 원상 복구 |
| 12 | 결제 콘솔에서 비용 할당 태그 `Project` 활성화 | 상태 "활성" | 태그가 나타나기까지 최대 24시간 |
| 13 | `terraform destroy` → `yes` | "1 destroyed", 콘솔에서 버킷이 사라짐 | 장부에 있는 것만 지운다 |

## 9. 주의할 점

| 주의 | 이유 |
|---|---|
| `apply`·`destroy`에서 `yes`를 치기 전에 마지막 요약 줄을 읽는다 | `destroy`, `-/+`가 있으면 멈추고 이유를 확인한다 |
| `destroy`는 state에 있는 것을 **전부** 지운다 | 그래서 스택을 나눈다. `nat`를 지울 때 `network`가 함께 지워지지 않는다 |
| 가져온 뒤에는 콘솔에서 고치지 않는다 | 드리프트가 생기고, 다음 `apply`가 콘솔 변경을 되돌린다([ADR-012](../10-adr.md#adr-012-인프라를-콘솔로-먼저-만들고-terraform으로-가져온다)) |
| state 파일은 커밋하지 않고 지우지도 않는다 | 평문이 들어 있다. 잃어버리면 Terraform이 리소스를 잊어 다시 import해야 한다 |
| 버킷에 객체가 있으면 `destroy`가 실패한다 | `force_destroy = false`가 기본이라 빈 버킷만 지운다 |
