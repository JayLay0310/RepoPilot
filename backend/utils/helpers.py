from pathlib import Path


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in {".py", ".java", ".md", ".txt", ".json", ".yaml", ".yml", ".xml", ".ini", ".toml"}
