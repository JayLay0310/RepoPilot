import re

from backend.parser.base_parser import BaseParser

try:
    import javalang
except Exception:  # pragma: no cover
    javalang = None


class JavaParser(BaseParser):
    def parse(self, code: str) -> dict:
        if javalang is not None:
            tree = javalang.parse.parse(code)
            classes = [node.name for _, node in tree.filter(javalang.tree.ClassDeclaration)]
            methods = [node.name for _, node in tree.filter(javalang.tree.MethodDeclaration)]
            annotations = [node.name for _, node in tree.filter(javalang.tree.Annotation)]
        else:
            classes = re.findall(r"class\s+([A-Za-z_][A-Za-z0-9_]*)", code)
            methods = re.findall(r"(?:public|private|protected)?\s*[\w<>\[\]]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*\{", code)
            annotations = re.findall(r"@([A-Za-z_][A-Za-z0-9_]*)", code)

        roles = {
            "controller": [c for c in classes if c.lower().endswith("controller")],
            "service": [c for c in classes if c.lower().endswith("service")],
            "mapper": [c for c in classes if c.lower().endswith("mapper")],
        }
        return {
            "language": "java",
            "classes": sorted(set(classes)),
            "methods": sorted(set(methods)),
            "annotations": sorted(set(annotations)),
            "roles": roles,
            "call_graph": {},
        }
