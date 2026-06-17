import ast
from collections import defaultdict

from backend.parser.base_parser import BaseParser


class PythonParser(BaseParser):
    def parse(self, code: str) -> dict:
        tree = ast.parse(code)
        functions, classes, imports = [], [], []
        graph = defaultdict(list)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                        graph[node.name].append(child.func.id)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.unparse(node) if hasattr(ast, "unparse") else str(type(node).__name__))

        return {
            "language": "python",
            "functions": sorted(set(functions)),
            "classes": sorted(set(classes)),
            "imports": imports,
            "call_graph": dict(graph),
        }
