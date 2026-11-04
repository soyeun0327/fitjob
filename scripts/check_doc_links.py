"""문서 링크·앵커 검사 (하네스 2-4).

저장소의 모든 *.md에서 상대 링크가 가리키는 파일과 섹션 앵커(GitHub 규칙)가
실제로 있는지 확인한다. 외부 URL(http 등)은 검사하지 않는다.

사용법 (저장소 루트에서, WSL):
    wsl -e python3 scripts/check_doc_links.py            # 전체 검사
    wsl -e python3 scripts/check_doc_links.py docs/a.md  # 지정한 파일의 링크만 검사
    ... | wsl -e python3 scripts/check_doc_links.py --hook
        # Claude Code PostToolUse 훅: 표준 입력의 JSON에서 수정한 파일을 보고,
        # *.md면 전체를 검사한다(제목이 바뀌면 다른 문서의 앵커가 깨지므로).

문제가 있으면 위치·원인·고치는 방법을 출력하고 종료 코드 1로 끝난다.
훅 모드는 문제를 표준 오류로 내고 종료 코드 2로 끝나 Claude가 바로 고치게 한다.
"""

from __future__ import annotations

import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", ".terraform", ".venv", "venv", "dist", "build"}
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def slugify(text: str) -> str:
    """GitHub 헤딩 앵커 규칙: 소문자, 글자·숫자·-·_만 남기고, 공백은 -로."""
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    out = []
    for ch in text.strip().lower():
        cat = unicodedata.category(ch)
        if ch in "-_" or cat[0] in ("L", "N") or cat == "Mn":
            out.append(ch)
        elif ch == " ":
            out.append("-")
    return "".join(out)


def iter_lines(path: Path):
    """코드 블록 밖의 줄만 (줄 번호, 내용)으로 돌려준다."""
    in_fence = False
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield lineno, line


def anchors_of(path: Path) -> list[str]:
    seen: dict[str, int] = {}
    result = []
    for _, line in iter_lines(path):
        m = HEADING_RE.match(line)
        if not m:
            continue
        base = slugify(m.group(2))
        n = seen.get(base, 0)
        result.append(base if n == 0 else f"{base}-{n}")
        seen[base] = n + 1
    return result


def md_files() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("*.md") if not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts)
    )


def check(files: list[Path]) -> tuple[int, list[str]]:
    cache: dict[Path, list[str]] = {}
    problems: list[str] = []
    total = 0
    for md in files:
        for lineno, line in iter_lines(md):
            for target in LINK_RE.findall(line):
                if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):  # http:, mailto: 등
                    continue
                total += 1
                file_part, _, anchor = target.partition("#")
                dest = (md.parent / file_part).resolve() if file_part else md
                where = f"{md.relative_to(ROOT).as_posix()}:{lineno}"
                if not dest.exists():
                    problems.append(
                        f"{where}: 링크한 파일이 없다 -> {target}\n"
                        f"  고치는 법: 링크는 이 문서 위치 기준 상대 경로다. 파일 이름이 바뀌었는지 확인하고 경로를 고친다."
                    )
                    continue
                if not anchor or dest.suffix != ".md":
                    continue
                if dest not in cache:
                    cache[dest] = anchors_of(dest)
                if anchor not in cache[dest]:
                    close = difflib.get_close_matches(anchor, cache[dest], n=3, cutoff=0.4)
                    hint = f" 비슷한 앵커: {', '.join('#' + c for c in close)}" if close else ""
                    problems.append(
                        f"{where}: 섹션 앵커가 없다 -> {target}\n"
                        f"  고치는 법: 대상 문서의 제목이 바뀌었을 수 있다. 앵커는 제목을 소문자로 바꾸고 "
                        f"글자·숫자·-·_만 남긴 뒤 공백을 -로 바꾼 값이다(점·괄호·쉼표는 빠짐).{hint}"
                    )
    return total, problems


def hook() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    edited = (data.get("tool_input") or {}).get("file_path") or (data.get("tool_response") or {}).get("filePath") or ""
    if not str(edited).lower().endswith(".md"):
        return 0
    total, problems = check(md_files())
    if not problems:
        return 0
    print("\n".join(problems), file=sys.stderr)
    print(f"문서 링크 검사: 링크 {total}개, 문제 {len(problems)}건. 위 링크를 고친 뒤 다시 저장하라.", file=sys.stderr)
    return 2


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if argv == ["--hook"]:
        return hook()
    if argv:
        files = [Path(a).resolve() for a in argv if a.endswith(".md") and Path(a).exists()]
    else:
        files = md_files()
    total, problems = check(files)
    for p in problems:
        print(p)
    print(f"문서 링크 검사: 링크 {total}개, 문제 {len(problems)}건")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
