from backend.parser.java_parser import JavaParser
from backend.parser.python_parser import PythonParser


class CodeAnalyzer:
    def __init__(self) -> None:
        self._parsers = {
            "python": PythonParser(),
            "java": JavaParser(),
        }

    def analyze(self, code: str, language: str) -> dict:
        parser = self._parsers.get(language.lower())
        if parser is None:
            raise ValueError(f"Unsupported language: {language}")
        parsed = parser.parse(code)
        parsed["complexity"] = max(len(parsed.get("functions", [])), len(parsed.get("methods", [])))
        parsed["dependencies"] = parsed.get("imports", [])
        return parsed
