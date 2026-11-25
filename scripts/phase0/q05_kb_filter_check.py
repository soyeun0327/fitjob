"""Phase 0 Q-05 실측: S3 Vectors를 벡터 저장소로 쓰는 Bedrock KB의 메타데이터 필터 동작.

실행(저장소 루트에서, 먼저 WSL 터미널에서 `aws login --remote`):
  wsl -e python3 scripts/phase0/q05_kb_filter_check.py            계획만 출력한다(AWS 호출 없음)
  wsl -e python3 scripts/phase0/q05_kb_filter_check.py --run      생성 → 시험 → 삭제
  wsl -e python3 scripts/phase0/q05_kb_filter_check.py --cleanup  중간에 멈췄을 때 남은 리소스만 지운다

확인하는 것(docs/04-api-spec.md 5.2 표, docs/09-roadmap.md Phase 0, 위험 R-10):
  1. 목록 메타데이터에 listContains, equals, in이 되는가
  2. andAll에 조건 6개·8개, orAll에 조건 19개, 2단계 중첩이 되는가
  3. 키가 없는 문서가 비교·목록 필터에서 빠지는가(notEquals는 예외인가)
  4. 빈 목록([]) 메타데이터를 받아주는가, 목록 필터에서 빠지는가
기대값은 문서에 적힌 동작을 옮긴 local_eval()로 계산한다. 실제 결과가 다르면 그 차이가 답이다.
AWS CLI를 subprocess로 부른다. 리소스 이름이 고정이라 --cleanup이 다시 찾아 지울 수 있다.
비용: Titan 임베딩 약 2천 토큰, S3 Vectors 쓰기·조회 수십 건, S3 요청 수십 건. 합계 1센트 미만.
결과 기록: docs/01-requirements.md Q-05, docs/04-api-spec.md 5.2, docs/03-db-schema.md 9
"""
import argparse
import datetime
import functools
import json
import os
import subprocess
import sys
import tempfile
import time

print = functools.partial(print, flush=True)  # 백그라운드 실행에서도 진행 상황이 바로 보이게

REGION = "ap-northeast-2"
TAGS = {"Project": "fitjob", "Env": "prod", "Stack": "practice", "ManagedBy": "script"}
EMBED_ID = "amazon.titan-embed-text-v2:0"
VEC_BUCKET = "fitjob-prod-q05-vectors"
INDEX = "postings"
ROLE = "fitjob-prod-q05-kb-role"
POLICY = "q05-kb"
KB_NAME = "fitjob-prod-q05-kb"
DS_NAME = "q05-docs"
PREFIX = "kb/postings/"
QUERY = "채용 공고"
TOP_K = 20  # 문서 수(10)보다 크게 잡아 필터를 통과한 문서가 모두 나오게 한다

KST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = (datetime.datetime.now(KST).date() - datetime.date(1970, 1, 1)).days
REGIONS_ALL = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원",
               "충북", "충남", "전북", "전남", "경북", "경남", "제주", "해외", "전국"]  # 19개


def m(career, years, cats, regions, emps, edu, deadline):
    """KB 메타데이터(docs/03-db-schema.md 9). None인 키는 넣지 않는다(키가 없는 문서 시험용)."""
    d = {"career_type": career, "career_min_years": years, "categories": cats, "regions": regions,
         "employment_types": emps, "education_level": edu, "deadline_epoch_day": deadline}
    return {k: v for k, v in d.items() if v is not None}


# 1단계 문서 8개. D04의 99는 연차 미상 표시값, D07은 어제 마감, D08은 career_min_years·employment_types 키 없음
DOCS_A = {
    "D01": ("서울 백엔드 신입", m("NEW", 0, ["BACKEND"], ["서울"], ["FULL_TIME"], "BACHELOR", TODAY + 5)),
    "D02": ("서울·경기 클라우드 인프라", m("ANY", 0, ["INFRA_CLOUD", "DEVOPS_SRE"], ["서울", "경기"], ["FULL_TIME"], "ANY", TODAY + 20)),
    "D03": ("부산 인프라 경력 3년", m("EXPERIENCED", 3, ["INFRA_CLOUD"], ["부산"], ["CONTRACT"], "BACHELOR", TODAY + 3)),
    "D04": ("전국 공공기관 전산직 경력", m("EXPERIENCED", 99, ["IT_GENERAL"], ["전국"], ["PERMANENT_CONTRACT"], "ASSOCIATE", 99999)),
    "D05": ("전남·광주 사무 보조 신입", m("NEW", 0, ["ETC"], ["전남", "광주"], ["CONTRACT", "INTERN"], "HIGH_SCHOOL", TODAY + 10)),
    "D06": ("대전 정보보안 경력 5년", m("EXPERIENCED", 5, ["SECURITY", "IT_GENERAL"], ["대전"], ["FULL_TIME", "CONTRACT"], "MASTER", TODAY + 30)),
    "D07": ("서울 경영지원 (어제 마감)", m("ANY", 0, ["MANAGEMENT"], ["서울"], ["PART_TIME"], "ANY", TODAY - 1)),
    "D08": ("인천 데이터 신입 (키 없음)", m("NEW", None, ["DATA"], ["인천"], None, "BACHELOR", TODAY + 7)),
}
# 2단계 문서 2개. 빈 목록이 동기화를 깨뜨려도 1단계 시험은 끝난 뒤라서 따로 넣는다
DOCS_B = {
    "D09": ("지역 매핑 실패 백엔드 (regions 빈 목록)", m("ANY", 0, ["BACKEND"], [], ["FULL_TIME"], "ANY", TODAY + 15)),
    "D10": ("직무·고용형태 매핑 실패 (빈 목록 2개)", m("NEW", 0, [], ["서울"], [], "BACHELOR", TODAY + 15)),
}


def eq(k, v): return {"equals": {"key": k, "value": v}}
def ne(k, v): return {"notEquals": {"key": k, "value": v}}
def in_(k, v): return {"in": {"key": k, "value": v}}
def nin(k, v): return {"notIn": {"key": k, "value": v}}
def lc(k, v): return {"listContains": {"key": k, "value": v}}
def lte(k, v): return {"lessThanOrEquals": {"key": k, "value": v}}
def gte(k, v): return {"greaterThanOrEquals": {"key": k, "value": v}}
def AND(*c): return {"andAll": list(c)}
def OR(*c): return {"orAll": list(c)}


SIX = [in_("career_type", ["EXPERIENCED", "ANY"]), lte("career_min_years", 5),
       gte("deadline_epoch_day", TODAY), lte("deadline_epoch_day", 99999),
       in_("education_level", ["ANY", "HIGH_SCHOOL", "ASSOCIATE", "BACHELOR", "MASTER"]),
       lc("employment_types", "FULL_TIME")]

# (ID, 설명, 필터). 설명의 "(탐색)"은 문서가 동작을 분명히 적지 않은 시험이다
TESTS_A = [
    ("A01", "equals 단일값", eq("career_type", "NEW")),
    ("A02", "in 단일값", in_("career_type", ["NEW", "ANY"])),
    ("A03", "notIn 단일값", nin("career_type", ["EXPERIENCED"])),
    ("A04", "listContains 목록", lc("regions", "서울")),
    ("A05", "(탐색) equals를 목록 키에", eq("regions", "서울")),
    ("A06", "(탐색) in을 목록 키에", in_("regions", ["부산", "대전"])),
    ("A07", "orAll 2개: 서울 또는 전국", OR(lc("regions", "서울"), lc("regions", "전국"))),
    ("A08", "숫자 <= 3, 99와 키 없음은 빠져야 함", lte("career_min_years", 3)),
    ("A09", "(탐색) notEquals 99, 키 없는 문서도 나오나", ne("career_min_years", 99)),
    ("A10", "listContains, 키 없는 문서는 빠져야 함", lc("employment_types", "FULL_TIME")),
    ("A11", "마감 >= 오늘", gte("deadline_epoch_day", TODAY)),
    ("A12", "andAll 조건 6개 (문서상 한도 5)", AND(*SIX)),
    ("A13", "andAll 조건 8개 + orAll 중첩", AND(*SIX, OR(*[lc("regions", r) for r in ["서울", "경기", "대전", "전국"]]),
                                          OR(lc("categories", "SECURITY"), lc("categories", "IT_GENERAL")))),
    ("A14", "orAll 조건 19개 (지역 전체)", OR(*[lc("regions", r) for r in REGIONS_ALL])),
    ("A15", "2단계 중첩 andAll>orAll>andAll", AND(gte("deadline_epoch_day", TODAY), OR(
        AND(eq("career_type", "NEW"), lc("regions", "서울")),
        AND(eq("career_type", "EXPERIENCED"), lc("regions", "부산"))))),
    ("A16", "설계 예시(API 명세 5.2): 서울·신입·인프라", AND(
        in_("career_type", ["NEW", "ANY"]),
        OR(lc("regions", "서울"), lc("regions", "전국")),
        OR(lc("categories", "INFRA_CLOUD"), lc("categories", "IT_GENERAL")),
        gte("deadline_epoch_day", TODAY))),
]
TESTS_B = [
    ("B01", "필터 없음: 빈 목록 문서도 색인됐나", None),
    ("B02", "listContains 서울, regions=[] 문서는 빠져야 함", lc("regions", "서울")),
    ("B03", "listContains BACKEND, categories=[] 문서는 빠져야 함", lc("categories", "BACKEND")),
    ("B04", "orAll 고용형태 2개, []와 키 없음은 빠져야 함", OR(lc("employment_types", "FULL_TIME"), lc("employment_types", "CONTRACT"))),
    ("B05", "orAll 지역 19개, regions=[] 문서는 빠져야 함", OR(*[lc("regions", r) for r in REGIONS_ALL])),
]


def local_eval(f, md):
    """문서에 적힌 동작의 모형. 목록에 equals·in은 원소 하나만 맞아도 참(S3 Vectors $eq 설명),
    키가 없으면 notEquals만 참(Retrieve API 설명), 빈 목록은 어떤 목록 필터도 통과하지 못한다."""
    if f is None:
        return True
    (op, arg), = f.items()
    if op == "andAll":
        return all(local_eval(c, md) for c in arg)
    if op == "orAll":
        return any(local_eval(c, md) for c in arg)
    k, v = arg["key"], arg["value"]
    if k not in md:
        return op == "notEquals"
    x = md[k]
    if op == "equals":
        return v in x if isinstance(x, list) else x == v
    if op == "notEquals":
        return v not in x if isinstance(x, list) else x != v
    if op == "in":
        return any(e in v for e in x) if isinstance(x, list) else x in v
    if op == "notIn":
        return not any(e in v for e in x) if isinstance(x, list) else x not in v
    if op == "listContains":
        return isinstance(x, list) and v in x
    if op == "lessThanOrEquals":
        return x <= v
    if op == "greaterThanOrEquals":
        return x >= v
    raise ValueError(op)


def expected(f, docs):
    return {d for d, (_, md) in docs.items() if local_eval(f, md)}


def aws(args, check=True):
    p = subprocess.run(["aws", *args, "--region", REGION, "--output", "json"], capture_output=True, text=True)
    data = {}
    if p.stdout.strip():
        try:
            data = json.loads(p.stdout)
        except json.JSONDecodeError:
            data = {"_text": p.stdout.strip()}
    if check and p.returncode != 0:
        raise RuntimeError(f"aws {' '.join(args[:2])} 실패: {p.stderr.strip()[:600]}")
    return p.returncode, data, p.stderr.strip()


def wait_until(fn, timeout, label, interval=5):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if fn():
            print(f"  {label} ({time.time() - t0:.0f}초)")
            return True
        time.sleep(interval)
    print(f"  [시간 초과] {label} ({timeout}초)")
    return False


def names(account):
    return {"doc_bucket": f"fitjob-prod-q05-docs-{account}",
            "embed_arn": f"arn:aws:bedrock:{REGION}::foundation-model/{EMBED_ID}",
            "index_arn": f"arn:aws:s3vectors:{REGION}:{account}:bucket/{VEC_BUCKET}/index/{INDEX}"}


def find_kb_id():
    rc, data, _ = aws(["bedrock-agent", "list-knowledge-bases"], check=False)
    for kb in data.get("knowledgeBaseSummaries", []) if rc == 0 else []:
        if kb["name"] == KB_NAME:
            return kb["knowledgeBaseId"]
    return None


def existing(account):
    n = names(account)
    found = []
    if aws(["s3api", "head-bucket", "--bucket", n["doc_bucket"]], check=False)[0] == 0:
        found.append(f"S3 버킷 {n['doc_bucket']}")
    if aws(["s3vectors", "get-vector-bucket", "--vector-bucket-name", VEC_BUCKET], check=False)[0] == 0:
        found.append(f"벡터 버킷 {VEC_BUCKET}")
    if aws(["iam", "get-role", "--role-name", ROLE], check=False)[0] == 0:
        found.append(f"IAM 역할 {ROLE}")
    if find_kb_id():
        found.append(f"KB {KB_NAME}")
    return found


def write_docs(docs, folder):
    os.makedirs(folder, exist_ok=True)
    for i, (key, (title, md)) in enumerate(docs.items()):
        pid = int(key[1:])
        meta = {"posting_id": pid, "source": "alio" if pid % 2 else "saramin", **md}
        text = (f"[공고] {title}\n직무: {', '.join(md.get('categories', [])) or '미상'}\n"
                f"지역: {', '.join(md.get('regions', [])) or '미상'}\n경력: {md['career_type']}\n"
                f"요약: Phase 0 필터 실측용 가짜 공고다.\n")
        with open(os.path.join(folder, f"{key}.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        with open(os.path.join(folder, f"{key}.txt.metadata.json"), "w", encoding="utf-8") as f:
            json.dump({"metadataAttributes": meta}, f, ensure_ascii=False)


def create(account, tmp):
    n = names(account)
    tag_list = [{"Key": k, "Value": v} for k, v in TAGS.items()]
    print("\n=== 생성")
    aws(["s3api", "create-bucket", "--bucket", n["doc_bucket"],
         "--create-bucket-configuration", f"LocationConstraint={REGION}"])
    aws(["s3api", "put-bucket-tagging", "--bucket", n["doc_bucket"], "--tagging", json.dumps({"TagSet": tag_list})])
    print(f"  S3 버킷 {n['doc_bucket']}")
    aws(["s3vectors", "create-vector-bucket", "--vector-bucket-name", VEC_BUCKET, "--tags", json.dumps(TAGS)])
    aws(["s3vectors", "create-index", "--vector-bucket-name", VEC_BUCKET, "--index-name", INDEX,
         "--data-type", "float32", "--dimension", "1024", "--distance-metric", "cosine",
         "--metadata-configuration", json.dumps({"nonFilterableMetadataKeys": ["AMAZON_BEDROCK_TEXT", "AMAZON_BEDROCK_METADATA"]}),
         "--tags", json.dumps(TAGS)])
    _, idx, _ = aws(["s3vectors", "get-index", "--vector-bucket-name", VEC_BUCKET, "--index-name", INDEX])
    index_arn = idx.get("index", {}).get("indexArn", n["index_arn"])
    print(f"  벡터 버킷 {VEC_BUCKET}, 인덱스 {INDEX} ({index_arn})")

    trust = {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Principal": {"Service": "bedrock.amazonaws.com"}, "Action": "sts:AssumeRole",
        "Condition": {"StringEquals": {"aws:SourceAccount": account},
                      "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock:{REGION}:{account}:knowledge-base/*"}}}]}
    own = {"aws:ResourceAccount": account}
    policy = {"Version": "2012-10-17", "Statement": [
        {"Sid": "Embed", "Effect": "Allow", "Action": "bedrock:InvokeModel", "Resource": n["embed_arn"]},
        {"Sid": "ListDocs", "Effect": "Allow", "Action": "s3:ListBucket",
         "Resource": f"arn:aws:s3:::{n['doc_bucket']}", "Condition": {"StringEquals": own}},
        {"Sid": "ReadDocs", "Effect": "Allow", "Action": "s3:GetObject",
         "Resource": f"arn:aws:s3:::{n['doc_bucket']}/*", "Condition": {"StringEquals": own}},
        {"Sid": "Vectors", "Effect": "Allow", "Resource": index_arn, "Action": [
            "s3vectors:GetIndex", "s3vectors:PutVectors", "s3vectors:GetVectors",
            "s3vectors:DeleteVectors", "s3vectors:QueryVectors"]}]}
    _, r, _ = aws(["iam", "create-role", "--role-name", ROLE, "--assume-role-policy-document", json.dumps(trust),
                   "--description", "Phase 0 Q-05 filter test, delete same day", "--tags", json.dumps(tag_list)])
    role_arn = r["Role"]["Arn"]
    aws(["iam", "put-role-policy", "--role-name", ROLE, "--policy-name", POLICY, "--policy-document", json.dumps(policy)])
    print(f"  IAM 역할 {ROLE} (권한 전파 대기 10초)")
    time.sleep(10)

    kb_cfg = {"type": "VECTOR", "vectorKnowledgeBaseConfiguration": {
        "embeddingModelArn": n["embed_arn"],
        "embeddingModelConfiguration": {"bedrockEmbeddingModelConfiguration": {"dimensions": 1024, "embeddingDataType": "FLOAT32"}}}}
    st_cfg = {"type": "S3_VECTORS", "s3VectorsConfiguration": {"indexArn": index_arn}}
    for attempt in range(8):
        rc, data, err = aws(["bedrock-agent", "create-knowledge-base", "--name", KB_NAME, "--role-arn", role_arn,
                             "--knowledge-base-configuration", json.dumps(kb_cfg),
                             "--storage-configuration", json.dumps(st_cfg), "--tags", json.dumps(TAGS)], check=False)
        if rc == 0:
            break
        if attempt < 7 and ("ValidationException" in err or "AccessDenied" in err):
            print(f"  KB 생성 재시도 {attempt + 1}/7 (IAM 전파 대기): {err.splitlines()[-1][:200]}")
            time.sleep(10)
            continue
        raise RuntimeError(f"KB 생성 실패: {err[:600]}")
    kb_id = data["knowledgeBase"]["knowledgeBaseId"]

    def kb_ready():
        _, d, _ = aws(["bedrock-agent", "get-knowledge-base", "--knowledge-base-id", kb_id])
        st = d["knowledgeBase"]["status"]
        if st == "FAILED":
            raise RuntimeError(f"KB 실패: {d['knowledgeBase'].get('failureReasons')}")
        return st == "ACTIVE"
    wait_until(kb_ready, 300, f"KB {kb_id} ACTIVE")

    _, ds, _ = aws(["bedrock-agent", "create-data-source", "--knowledge-base-id", kb_id, "--name", DS_NAME,
                    "--data-source-configuration", json.dumps({"type": "S3", "s3Configuration": {
                        "bucketArn": f"arn:aws:s3:::{n['doc_bucket']}", "inclusionPrefixes": [PREFIX]}}),
                    "--vector-ingestion-configuration", json.dumps({"chunkingConfiguration": {"chunkingStrategy": "NONE"}}),
                    "--data-deletion-policy", "RETAIN"])
    ds_id = ds["dataSource"]["dataSourceId"]
    print(f"  데이터 소스 {ds_id} (분할 없음)")
    return kb_id, ds_id


def upload(account, folder):
    aws(["s3", "cp", folder, f"s3://{names(account)['doc_bucket']}/{PREFIX}", "--recursive", "--only-show-errors"])


def ingest(kb_id, ds_id, label):
    _, d, _ = aws(["bedrock-agent", "start-ingestion-job", "--knowledge-base-id", kb_id, "--data-source-id", ds_id])
    job_id = d["ingestionJob"]["ingestionJobId"]
    t0 = time.time()
    while True:
        _, d, _ = aws(["bedrock-agent", "get-ingestion-job", "--knowledge-base-id", kb_id,
                       "--data-source-id", ds_id, "--ingestion-job-id", job_id])
        job = d["ingestionJob"]
        if job["status"] in ("COMPLETE", "FAILED", "STOPPED"):
            break
        if time.time() - t0 > 600:
            raise RuntimeError("동기화가 10분을 넘었다")
        time.sleep(10)
    print(f"\n=== 동기화 {label}: {job['status']} ({time.time() - t0:.0f}초)")
    print(f"  통계 {json.dumps(job.get('statistics', {}))}")
    for reason in job.get("failureReasons", []):
        print(f"  실패 이유: {reason[:500]}")
    time.sleep(5)
    return job


def retrieve(kb_id, flt):
    vs = {"numberOfResults": TOP_K}
    if flt is not None:
        vs["filter"] = flt
    t0 = time.time()
    rc, data, err = aws(["bedrock-agent-runtime", "retrieve", "--knowledge-base-id", kb_id,
                         "--retrieval-query", json.dumps({"text": QUERY}, ensure_ascii=False),
                         "--retrieval-configuration", json.dumps({"vectorSearchConfiguration": vs}, ensure_ascii=False)],
                        check=False)
    ms = (time.time() - t0) * 1000
    if rc != 0:
        return None, err.splitlines()[-1][:300] if err else "오류", ms
    got = {r["location"]["s3Location"]["uri"].rsplit("/", 1)[-1].split(".")[0] for r in data.get("retrievalResults", [])}
    return got, None, ms


def run_tests(kb_id, tests, docs, results):
    for tid, desc, flt in tests:
        exp = expected(flt, docs)
        got, err, ms = retrieve(kb_id, flt)
        verdict = "오류" if err else ("같음" if got == exp else "다름")
        results.append((tid, verdict, desc, exp, got, err))
        print(f"\n[{tid}] {verdict} | {desc} | {ms:.0f}ms")
        print(f"  필터 {json.dumps(flt, ensure_ascii=False) if flt else '없음'}")
        print(f"  기대 {sorted(exp)}")
        print(f"  실제 {sorted(got) if got is not None else err}")
        if got is not None and got != exp:
            print(f"  더 나옴 {sorted(got - exp)} / 빠짐 {sorted(exp - got)}")


def dump_metadata(keys):
    """KB가 S3 Vectors에 저장한 메타데이터를 그대로 본다(빈 목록·없는 키가 어떻게 저장됐나)."""
    rc, data, err = aws(["s3vectors", "list-vectors", "--vector-bucket-name", VEC_BUCKET,
                         "--index-name", INDEX, "--return-metadata"], check=False)
    print("\n=== 저장된 메타데이터 (S3 Vectors list-vectors)")
    if rc != 0:
        print(f"  조회 실패: {err[:300]}")
        return
    for v in data.get("vectors", []):
        md = v.get("metadata", {})
        blob = json.dumps(md, ensure_ascii=False)
        doc = next((k for k in keys if f"/{k}.txt" in blob), None)
        if doc:
            shown = {k: (x if len(str(x)) <= 120 else str(x)[:120] + "...") for k, x in md.items() if k != "AMAZON_BEDROCK_TEXT"}
            print(f"  {doc}: {json.dumps(shown, ensure_ascii=False)}")


def step(label, args):
    rc, _, err = aws(args, check=False)
    if rc == 0:
        print(f"  {label}: 삭제")
    elif any(s in err for s in ("NotFound", "NoSuchBucket", "NoSuchEntity", "does not exist", "404")):
        print(f"  {label}: 없음")
    else:
        print(f"  {label}: 실패 {err.splitlines()[-1][:300] if err else ''}")


def cleanup(account):
    n = names(account)
    print("\n=== 정리(삭제)")
    kb_id = find_kb_id()
    if kb_id:
        rc, data, _ = aws(["bedrock-agent", "list-data-sources", "--knowledge-base-id", kb_id], check=False)
        for ds in data.get("dataSourceSummaries", []) if rc == 0 else []:
            step(f"데이터 소스 {ds['dataSourceId']}", ["bedrock-agent", "delete-data-source",
                                                   "--knowledge-base-id", kb_id, "--data-source-id", ds["dataSourceId"]])
        step(f"KB {kb_id}", ["bedrock-agent", "delete-knowledge-base", "--knowledge-base-id", kb_id])
        wait_until(lambda: aws(["bedrock-agent", "get-knowledge-base", "--knowledge-base-id", kb_id], check=False)[0] != 0,
                   300, "KB 삭제 완료")
    else:
        print("  KB: 없음")
    step(f"벡터 인덱스 {INDEX}", ["s3vectors", "delete-index", "--vector-bucket-name", VEC_BUCKET, "--index-name", INDEX])
    step(f"벡터 버킷 {VEC_BUCKET}", ["s3vectors", "delete-vector-bucket", "--vector-bucket-name", VEC_BUCKET])
    step(f"S3 버킷 {n['doc_bucket']}", ["s3", "rb", f"s3://{n['doc_bucket']}", "--force"])
    step(f"역할 정책 {POLICY}", ["iam", "delete-role-policy", "--role-name", ROLE, "--policy-name", POLICY])
    step(f"IAM 역할 {ROLE}", ["iam", "delete-role", "--role-name", ROLE])
    left = existing(account)
    print(f"  남은 리소스: {left or '없음'}")
    return left


def summary(results):
    print("\n=== 요약")
    for tid, verdict, desc, exp, got, err in results:
        detail = err if err else ("" if got == exp else f"더 나옴 {sorted(got - exp)} 빠짐 {sorted(exp - got)}")
        print(f"  {tid} {verdict:2} {desc} {detail}")


def plan():
    print(f"오늘 epoch day {TODAY} (KST {datetime.datetime.now(KST).date()})")
    print("\n만들 리소스(모두 서울, 태그 " + ", ".join(f"{k}={v}" for k, v in TAGS.items()) + "):")
    for r in ["S3 버킷 fitjob-prod-q05-docs-<계정ID> (가짜 공고 10개와 메타데이터 파일)",
              f"S3 Vectors 벡터 버킷 {VEC_BUCKET}, 인덱스 {INDEX} (1024차원, 코사인, 필터 불가 키 2개)",
              f"IAM 역할 {ROLE} (Titan 호출, 문서 버킷 읽기, 인덱스 읽기·쓰기)",
              f"Bedrock KB {KB_NAME} + 데이터 소스 {DS_NAME} (분할 없음)"]:
        print(f"  - {r}")
    for label, docs in (("1단계 문서", DOCS_A), ("2단계 문서", DOCS_B)):
        print(f"\n{label}:")
        for k, (title, md) in docs.items():
            print(f"  {k} {title}: {json.dumps(md, ensure_ascii=False)}")
    for label, tests, docs in (("1단계 시험 (D01~D08)", TESTS_A, DOCS_A), ("2단계 시험 (D01~D10)", TESTS_B, {**DOCS_A, **DOCS_B})):
        print(f"\n{label}:")
        for tid, desc, flt in tests:
            print(f"  {tid} {desc} → 기대 {sorted(expected(flt, docs))}")
    print("\n실행하려면 --run")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--run", action="store_true")
    g.add_argument("--cleanup", action="store_true")
    a = ap.parse_args()
    if not (a.run or a.cleanup):
        plan()
        return
    _, ident, _ = aws(["sts", "get-caller-identity"])
    account = ident["Account"]
    if a.cleanup:
        sys.exit(2 if cleanup(account) else 0)
    found = existing(account)
    if found:
        sys.exit(f"이전 실행의 리소스가 남아 있다: {found}. 먼저 --cleanup")
    results = []
    tmp = tempfile.mkdtemp(prefix="q05-")
    t0 = time.time()
    try:
        kb_id, ds_id = create(account, tmp)
        write_docs(DOCS_A, os.path.join(tmp, "a"))
        upload(account, os.path.join(tmp, "a"))
        job = ingest(kb_id, ds_id, "1단계 (D01~D08)")
        if job["status"] == "COMPLETE":
            run_tests(kb_id, TESTS_A, DOCS_A, results)
        write_docs(DOCS_B, os.path.join(tmp, "b"))
        upload(account, os.path.join(tmp, "b"))
        job = ingest(kb_id, ds_id, "2단계 (+D09, D10 빈 목록)")
        if job["status"] == "COMPLETE":
            run_tests(kb_id, TESTS_B, {**DOCS_A, **DOCS_B}, results)
        dump_metadata(["D01", "D04", "D08", "D09", "D10"])
    except Exception as e:  # 어떤 오류든 아래 정리는 반드시 한다
        print(f"\n[중단] {e}")
    finally:
        left = cleanup(account)
        summary(results)
        print(f"\n총 {time.time() - t0:.0f}초")
        if left:
            sys.exit("남은 리소스가 있다. --cleanup으로 다시 지운다")


if __name__ == "__main__":
    main()
