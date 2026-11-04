#!/usr/bin/env bash
# FitJob 개발 도구 설치 (WSL Ubuntu 24.04)
#
# 설치하는 것: make, Terraform, AWS CLI v2, Session Manager 플러그인
#   (로드맵 Phase 0 "WSL 개발 환경", 하네스 2-1)
# 실행: 저장소 루트에서 관리자 권한으로
#   Windows 셸:    wsl -u root -e bash scripts/setup-wsl.sh
#   WSL 터미널:    sudo bash scripts/setup-wsl.sh
# 이미 설치된 도구는 건너뛰므로 여러 번 실행해도 된다.
# AWS 자격증명은 설정하지 않는다. 작업용 IAM 사용자를 만든 뒤 사용자가 직접 한다.

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "관리자 권한이 필요하다. 'sudo bash scripts/setup-wsl.sh'로 실행하라." >&2
  exit 1
fi

# shellcheck source=/dev/null
. /etc/os-release
if [[ "${ID}" != "ubuntu" ]]; then
  echo "Ubuntu용 스크립트다. 현재 배포판: ${PRETTY_NAME}" >&2
  exit 1
fi

case "$(uname -m)" in
  x86_64)  AWSCLI_ARCH=x86_64;  SSM_DIR=ubuntu_64bit ;;
  aarch64) AWSCLI_ARCH=aarch64; SSM_DIR=ubuntu_arm64 ;;
  *) echo "지원하지 않는 CPU 아키텍처: $(uname -m)" >&2; exit 1 ;;
esac

export DEBIAN_FRONTEND=noninteractive
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

has() { command -v "$1" >/dev/null 2>&1; }

echo "== 1/4 기본 패키지 (make, curl, unzip, gnupg)"
apt-get update -qq
apt-get install -y -qq make curl unzip gnupg ca-certificates

echo "== 2/4 Terraform (HashiCorp 공식 apt 저장소)"
if has terraform; then
  echo "이미 있음: $(terraform version | sed -n 1p)"
else
  KEYRING=/usr/share/keyrings/hashicorp-archive-keyring.gpg
  curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor --yes -o "$KEYRING"
  echo "deb [arch=$(dpkg --print-architecture) signed-by=${KEYRING}] https://apt.releases.hashicorp.com ${VERSION_CODENAME} main" \
    > /etc/apt/sources.list.d/hashicorp.list
  apt-get update -qq
  apt-get install -y -qq terraform
fi

echo "== 3/4 AWS CLI v2 (AWS 공식 설치 파일)"
if has aws && [[ "$(aws --version 2>&1)" == aws-cli/2* ]]; then
  echo "이미 있음: $(aws --version 2>&1)"
else
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${AWSCLI_ARCH}.zip" -o "$TMP/awscliv2.zip"
  unzip -q "$TMP/awscliv2.zip" -d "$TMP"
  "$TMP/aws/install" --update
fi

echo "== 4/4 Session Manager 플러그인 (AWS 공식 .deb)"
if has session-manager-plugin; then
  echo "이미 있음: session-manager-plugin $(session-manager-plugin --version)"
else
  curl -fsSL "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/${SSM_DIR}/session-manager-plugin.deb" \
    -o "$TMP/session-manager-plugin.deb"
  dpkg -i "$TMP/session-manager-plugin.deb"
fi

echo "== 설치 결과"
make --version | sed -n 1p
terraform version | sed -n 1p
aws --version 2>&1
echo "session-manager-plugin $(session-manager-plugin --version)"
