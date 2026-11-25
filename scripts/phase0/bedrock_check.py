"""Phase 0 Q-03/Q-04 확인: 서울 리전 Haiku 5.5 호출 방식, Titan 임베딩 V2 한국어 품질.

실행: 저장소 루트에서 `wsl -e python3 scripts/phase0/bedrock_check.py` (먼저 `aws login --remote`)
AWS CLI를 subprocess로 부른다. 호출 수: converse 4회, 임베딩 9회. 비용 1센트 미만.
조건 추출 도구 스키마는 docs/04-api-spec.md 5.1과 같다(바꾸면 함께 고친다).
결과 기록: docs/01-requirements.md 9장 Q-03·Q-04 (2026-11-10 첫 실행, Haiku는 Anthropic 양식 미제출로 실패)
"""
import json
import math
import os
import subprocess
import tempfile
import time

HERE = tempfile.gettempdir()  # 임베딩 응답 임시 파일 위치(저장소 밖)

REGION = "ap-northeast-2"
PROFILE_ID = "global.anthropic.claude-haiku-5-5"
DIRECT_ID = "anthropic.claude-haiku-5-5"
EMBED_ID = "amazon.titan-embed-text-v2:0"

TOOL = {
    "name": "set_search_conditions",
    "description": "구직자의 메시지에서 채용공고 검색 조건을 추출한다. 메시지에 없는 조건은 비워 둔다.",
    "inputSchema": {"json": {
        "type": "object",
        "properties": {
            "intent": {"type": "string", "enum": ["SEARCH", "REFINE", "RESET", "OFF_TOPIC"],
                       "description": "SEARCH 새 검색, REFINE 직전 조건에 더하기, RESET 조건 초기화, OFF_TOPIC 채용과 무관"},
            "career": {"type": ["string", "null"], "enum": ["new", "experienced", None]},
            "career_years": {"type": ["integer", "null"], "minimum": 0, "maximum": 40},
            "regions": {"type": "array", "items": {"type": "string", "enum": [
                "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원",
                "충북", "충남", "전북", "전남", "경북", "경남", "제주", "해외"]}},
            "categories": {"type": "array", "items": {"type": "string", "enum": [
                "BACKEND", "FRONTEND", "MOBILE", "DATA", "AI_ML", "INFRA_CLOUD", "DEVOPS_SRE", "SECURITY",
                "QA", "EMBEDDED", "PM", "DESIGN", "MARKETING", "SALES", "MANAGEMENT", "ETC"]}},
            "employment_types": {"type": "array", "items": {"type": "string", "enum": [
                "FULL_TIME", "PERMANENT_CONTRACT", "CONTRACT", "INTERN", "PART_TIME"]}},
            "education": {"type": ["string", "null"],
                          "enum": ["HIGH_SCHOOL", "ASSOCIATE", "BACHELOR", "MASTER", "DOCTORATE", None],
                          "description": "구직자 본인의 최종 학력"},
            "deadline_within_days": {"type": ["integer", "null"], "minimum": 1, "maximum": 60},
            "semantic_query": {"type": "string",
                               "description": "필터로 표현되지 않는 직무 내용, 기술, 선호를 담은 검색 문장"},
        },
        "required": ["intent", "semantic_query"],
    }},
}
TOOL_CONFIG = {"tools": [{"toolSpec": TOOL}], "toolChoice": {"tool": {"name": "set_search_conditions"}}}


def aws(args):
    t0 = time.time()
    p = subprocess.run(["aws", *args, "--region", REGION, "--output", "json"], capture_output=True, text=True)
    return p, (time.time() - t0) * 1000


def converse(model_id, text):
    msgs = [{"role": "user", "content": [{"text": text}]}]
    return aws(["bedrock-runtime", "converse", "--model-id", model_id,
                "--messages", json.dumps(msgs, ensure_ascii=False),
                "--tool-config", json.dumps(TOOL_CONFIG, ensure_ascii=False),
                "--inference-config", json.dumps({"maxTokens": 500})])


def embed(text):
    body = json.dumps({"inputText": text, "dimensions": 1024, "normalize": True}, ensure_ascii=False)
    outfile = os.path.join(HERE, "embed_out.json")
    p, _ = aws(["bedrock-runtime", "invoke-model", "--model-id", EMBED_ID,
                "--cli-binary-format", "raw-in-base64-out", "--body", body, outfile])
    if p.returncode != 0:
        raise SystemExit(f"embed 실패: {p.stderr.strip()}")
    with open(outfile, encoding="utf-8") as f:
        r = json.load(f)
    return r["embedding"], r["inputTextTokenCount"]


def cos(a, b):
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


print("=== Q-03-1 기반 모델 ID로 직접 호출 (실패 예상)")
p, ms = converse(DIRECT_ID, "안녕")
print("returncode", p.returncode, "|", (p.stderr.strip().splitlines() or [""])[-1][:300])

print("\n=== Q-03-2 글로벌 추론 프로필 + 조건 추출 도구(강제 호출)")
for q in ["QA 3년차인데 인프라로 가고 싶어",
          "부산 사는 신입인데 정규직 간호사 자리 있어? 마감 일주일 안 남은 걸로",
          "오늘 날씨 어때?"]:
    p, ms = converse(PROFILE_ID, q)
    if p.returncode != 0:
        print(f"[실패] {q} | {p.stderr.strip()[:400]}")
        continue
    r = json.loads(p.stdout)
    tool = [c["toolUse"]["input"] for c in r["output"]["message"]["content"] if "toolUse" in c]
    print(f"- 질의: {q}")
    print(f"  결과: {json.dumps(tool[0] if tool else None, ensure_ascii=False)}")
    print(f"  stopReason={r['stopReason']} tokens(in/out)={r['usage']['inputTokens']}/{r['usage']['outputTokens']}"
          f" latencyMs(서버)={r['metrics']['latencyMs']} 왕복ms={ms:.0f}")

print("\n=== Q-04 Titan Text Embeddings V2 (1024차원) 한국어 유사도")
docs = {
    "D1 서울 백엔드 신입": "[서울 강남] 백엔드 개발자(Java/Spring) 신입 채용. 학력 무관, 정규직",
    "D2 서울 서버개발 신입": "[서울] 서버 개발 신입 사원 모집 - Python, Django 경험 우대",
    "D3 영문 백엔드": "Junior Backend Engineer (Seoul) - Spring Boot, AWS",
    "D4 서울 회계 신입": "[서울] 회계팀 신입 사원 채용, 정규직, 전산회계 자격 우대",
    "D5 부산 간호사 경력": "[부산] 병동 간호사 채용 (경력 3년 이상), 계약직",
    "D6 정보보안 관제": "정보보안 관제 요원 채용 - 보안 장비 운영, 침해사고 대응 (경력 2년 이상)",
}
queries = {
    "Q1": "서울에서 신입으로 지원할 수 있는 백엔드 개발자 공고",
    "Q2": "병원에서 환자 돌보는 일자리",
    "Q3": "사이버 보안 모니터링 업무",
}
vec, tok = {}, {}
for k, t in {**docs, **queries}.items():
    vec[k], tok[k] = embed(t)
for qk, qt in queries.items():
    ranked = sorted(docs, key=lambda d: cos(vec[qk], vec[d]), reverse=True)
    print(f"- {qk} {qt}")
    for d in ranked:
        print(f"    {cos(vec[qk], vec[d]):.3f}  {d}")
print("\n토큰 수(글자 수):", {k: f"{tok[k]}({len(t)})" for k, t in {**docs, **queries}.items()})
