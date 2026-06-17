import re
from pathlib import Path


def _safe_repo_path(repo_path: str) -> Path:
    root = Path.cwd().resolve()
    candidate = Path(repo_path).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError("repo_path must be inside the current workspace")
    if not candidate.exists() or not candidate.is_dir():
        raise ValueError("repo_path must be an existing directory")
    return candidate


def keyword_search(repo_path: str, keyword: str, top_k: int = 20) -> list[dict]:
    results = []
    for path in _safe_repo_path(repo_path).rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for idx, line in enumerate(text.splitlines(), start=1):
            if keyword.lower() in line.lower():
                results.append({"path": str(path), "line": idx, "content": line.strip()})
                if len(results) >= top_k:
                    return results
    return results


def regex_search(repo_path: str, pattern: str, top_k: int = 20) -> list[dict]:
    regex = re.compile(pattern)
    results = []
    for path in _safe_repo_path(repo_path).rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for idx, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                results.append({"path": str(path), "line": idx, "content": line.strip()})
                if len(results) >= top_k:
                    return results
    return results


def find_symbol(repo_path: str, symbol: str) -> list[dict]:
    pattern = rf"(?:public|private|protected)?\s*(?:class|def|interface)\s+{re.escape(symbol)}"
    return regex_search(repo_path, pattern, top_k=50)
