from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=512)
def read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def extract_snippet(path: str, start_line: int, end_line: int) -> str:
    lines = read_file(path).splitlines()
    start_line = max(start_line, 1)
    end_line = max(end_line, start_line)
    return "\n".join(lines[start_line - 1 : end_line])
