from collections import Counter
from pathlib import Path


def list_files(repo_path: str) -> list[str]:
    repo = Path(repo_path)
    return [str(p) for p in repo.rglob("*") if p.is_file()]


def file_type_stats(repo_path: str) -> dict[str, int]:
    counter = Counter(Path(path).suffix.lower() or "<none>" for path in list_files(repo_path))
    return dict(counter)


def detect_frameworks(repo_path: str) -> list[str]:
    files = set(Path(p).name for p in list_files(repo_path))
    frameworks = []
    if "pom.xml" in files or "build.gradle" in files:
        frameworks.append("spring-boot")
    if "manage.py" in files or "settings.py" in files:
        frameworks.append("django")
    if "requirements.txt" in files:
        frameworks.append("python")
    return frameworks


def scan_repo(repo_path: str) -> dict:
    files = list_files(repo_path)
    return {
        "file_count": len(files),
        "files": files,
        "file_types": file_type_stats(repo_path),
        "frameworks": detect_frameworks(repo_path),
    }
