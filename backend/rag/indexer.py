import ast
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.config import get_settings
from backend.rag.embeddings import EmbeddingService
from backend.rag.vector_store import FaissVectorStore
from backend.utils.helpers import is_text_file

try:
    import javalang
except Exception:  # pragma: no cover
    javalang = None

SKIP_DIRS = {".git", ".idea", ".venv", "__pycache__", "node_modules", ".faiss", ".cache", "dist", "build"}
INDEX_VERSION = 2
CHUNK_STRATEGY = "ast-aware-v1"
MAX_CHUNK_LINES = 80
FALLBACK_CHUNK_LINES = 40
FALLBACK_OVERLAP = 8


@dataclass
class CodeChunk:
    content: str
    start_line: int
    end_line: int
    chunk_type: str
    symbol: str
    language: str


def build_or_load_index(repo_path: str, force_rebuild: bool = False) -> dict[str, Any]:
    repo = Path(repo_path).resolve()
    persist_dir = repo / get_settings().vector_store_dir
    store = FaissVectorStore(str(persist_dir))

    if not force_rebuild:
        try:
            if store.load() and _store_matches_current_strategy(store):
                return {
                    "status": "loaded",
                    "chunks": len(store.records),
                    "index_dir": str(persist_dir),
                    "chunk_strategy": CHUNK_STRATEGY,
                }
        except Exception:
            pass

    documents = _collect_documents(repo)
    embeddings = EmbeddingService()
    vectors = embeddings.embed([doc["content"] for doc in documents])
    try:
        store.build(documents, vectors)
        store.save()
        status = "built"
    except Exception as exc:
        metadata_path = persist_dir / "metadata.json"
        payload = [{"record": doc, "vector": vector} for doc, vector in zip(documents, vectors)]
        metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        status = f"metadata_only: {exc}"

    return {
        "status": status,
        "chunks": len(documents),
        "index_dir": str(persist_dir),
        "chunk_strategy": CHUNK_STRATEGY,
    }


def _collect_documents(repo: Path) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for path in repo.rglob("*"):
        if _should_skip(path, repo) or not path.is_file() or not is_text_file(path):
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        rel_path = path.relative_to(repo).as_posix()
        for chunk_no, chunk in enumerate(_split_ast_aware_chunks(path, text)):
            if not chunk.content.strip():
                continue
            documents.append(
                {
                    "id": _stable_id(rel_path, chunk_no, chunk.content),
                    "path": str(path),
                    "relative_path": rel_path,
                    "line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "content": chunk.content,
                    "chunk_type": chunk.chunk_type,
                    "symbol": chunk.symbol,
                    "language": chunk.language,
                    "chunk_strategy": CHUNK_STRATEGY,
                    "index_version": INDEX_VERSION,
                }
            )
    return documents


def _split_ast_aware_chunks(path: Path, content: str) -> list[CodeChunk]:
    suffix = path.suffix.lower()
    if suffix == ".py":
        chunks = _split_python_chunks(content)
    elif suffix == ".java":
        chunks = _split_java_chunks(content)
    else:
        chunks = []

    if not chunks:
        language = suffix.lstrip(".") or "text"
        chunks = _split_line_chunks(content, language=language)
    return chunks


def _split_python_chunks(content: str) -> list[CodeChunk]:
    lines = content.splitlines()
    if not lines:
        return []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    header_end = _python_header_end(tree)
    header = _slice_lines(lines, 1, header_end)
    chunks: list[CodeChunk] = []
    covered_ranges: list[tuple[int, int]] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            chunks.extend(_python_class_chunks(lines, header, node))
            covered_ranges.append((_node_start(node), _node_end(node)))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunks.extend(
                _bounded_chunk(
                    lines,
                    start=_node_start(node),
                    end=_node_end(node),
                    prefix=header,
                    chunk_type="function",
                    symbol=node.name,
                    language="python",
                )
            )
            covered_ranges.append((_node_start(node), _node_end(node)))

    module_lines = _uncovered_top_level_ranges(lines, covered_ranges, start_after=header_end)
    for idx, (start, end) in enumerate(module_lines):
        chunks.extend(
            _bounded_chunk(
                lines,
                start=start,
                end=end,
                prefix=header,
                chunk_type="module",
                symbol=f"module_block_{idx}",
                language="python",
            )
        )
    return chunks


def _python_class_chunks(lines: list[str], header: str, class_node: ast.ClassDef) -> list[CodeChunk]:
    class_start = _node_start(class_node)
    class_end = _node_end(class_node)
    method_ranges = [
        (_node_start(child), _node_end(child))
        for child in class_node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    first_method_line = min((start for start, _ in method_ranges), default=class_end + 1)
    class_context_end = min(class_end, first_method_line - 1)
    class_context = _slice_lines(lines, class_start, class_context_end)
    prefix = _join_parts(header, class_context)
    chunks: list[CodeChunk] = []

    if not method_ranges:
        return _bounded_chunk(
            lines,
            start=class_start,
            end=class_end,
            prefix=header,
            chunk_type="class",
            symbol=class_node.name,
            language="python",
        )

    for child in class_node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunks.extend(
                _bounded_chunk(
                    lines,
                    start=_node_start(child),
                    end=_node_end(child),
                    prefix=prefix,
                    chunk_type="method",
                    symbol=f"{class_node.name}.{child.name}",
                    language="python",
                )
            )
    return chunks


def _split_java_chunks(content: str) -> list[CodeChunk]:
    lines = content.splitlines()
    if not lines or javalang is None:
        return []

    try:
        tree = javalang.parse.parse(content)
    except Exception:
        return []

    header = _java_header(lines, tree)
    chunks: list[CodeChunk] = []
    for _, class_node in tree.filter(javalang.tree.ClassDeclaration):
        class_start = _line(class_node)
        class_end = _java_class_end(lines, class_start)
        class_context = _java_class_context(lines, class_start, class_end)
        prefix = _join_parts(header, class_context)

        method_nodes = list(class_node.methods) + list(class_node.constructors)
        if not method_nodes:
            chunks.extend(
                _bounded_chunk(
                    lines,
                    start=class_start,
                    end=class_end,
                    prefix=header,
                    chunk_type="class",
                    symbol=class_node.name,
                    language="java",
                )
            )
            continue

        for method in method_nodes:
            method_start = _line(method)
            method_end = _java_member_end(lines, method_start)
            method_name = getattr(method, "name", class_node.name)
            chunks.extend(
                _bounded_chunk(
                    lines,
                    start=method_start,
                    end=method_end,
                    prefix=prefix,
                    chunk_type="method",
                    symbol=f"{class_node.name}.{method_name}",
                    language="java",
                )
            )
    return chunks


def _bounded_chunk(
    lines: list[str],
    start: int,
    end: int,
    prefix: str,
    chunk_type: str,
    symbol: str,
    language: str,
) -> list[CodeChunk]:
    body_lines = lines[start - 1 : end]
    if len(body_lines) <= MAX_CHUNK_LINES:
        content = _join_parts(prefix, "\n".join(body_lines))
        return [CodeChunk(content, start, end, chunk_type, symbol, language)]

    chunks = []
    for idx, line_chunk in enumerate(_line_windows(body_lines, max_lines=MAX_CHUNK_LINES, overlap=FALLBACK_OVERLAP)):
        chunk_start = start + idx * (MAX_CHUNK_LINES - FALLBACK_OVERLAP)
        chunk_end = min(chunk_start + len(line_chunk.splitlines()) - 1, end)
        content = _join_parts(prefix, line_chunk)
        chunks.append(CodeChunk(content, chunk_start, chunk_end, f"{chunk_type}_part", f"{symbol}#{idx + 1}", language))
    return chunks


def _split_line_chunks(content: str, language: str) -> list[CodeChunk]:
    lines = content.splitlines()
    chunks = []
    step = FALLBACK_CHUNK_LINES - FALLBACK_OVERLAP
    for idx, chunk in enumerate(_line_windows(lines, max_lines=FALLBACK_CHUNK_LINES, overlap=FALLBACK_OVERLAP)):
        start = idx * step + 1
        end = min(start + len(chunk.splitlines()) - 1, len(lines))
        chunks.append(CodeChunk(chunk, start, end, "line_window", f"window_{idx}", language))
    return chunks


def _line_windows(lines: list[str], max_lines: int, overlap: int) -> list[str]:
    if not lines:
        return []
    step = max_lines - overlap
    return ["\n".join(lines[i : i + max_lines]) for i in range(0, len(lines), step)]


def _python_header_end(tree: ast.Module) -> int:
    end = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            end = max(end, _node_end(node))
        elif isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and isinstance(node.value.value, str):
            end = max(end, _node_end(node))
        else:
            break
    return end


def _uncovered_top_level_ranges(lines: list[str], covered: list[tuple[int, int]], start_after: int) -> list[tuple[int, int]]:
    ranges = []
    current_start = start_after + 1
    for start, end in sorted(covered):
        if current_start < start:
            ranges.extend(_non_blank_ranges(lines, current_start, start - 1))
        current_start = max(current_start, end + 1)
    if current_start <= len(lines):
        ranges.extend(_non_blank_ranges(lines, current_start, len(lines)))
    return ranges


def _non_blank_ranges(lines: list[str], start: int, end: int) -> list[tuple[int, int]]:
    ranges = []
    current = None
    for line_no in range(start, end + 1):
        if lines[line_no - 1].strip():
            if current is None:
                current = line_no
        elif current is not None:
            ranges.append((current, line_no - 1))
            current = None
    if current is not None:
        ranges.append((current, end))
    return ranges


def _java_header(lines: list[str], tree: Any) -> str:
    header_end = 0
    if getattr(tree, "package", None) and getattr(tree.package, "position", None):
        header_end = max(header_end, tree.package.position.line)
    for import_node in getattr(tree, "imports", []) or []:
        if getattr(import_node, "position", None):
            header_end = max(header_end, import_node.position.line)
    return _slice_lines(lines, 1, header_end)


def _java_class_context(lines: list[str], class_start: int, class_end: int) -> str:
    context_lines = []
    for line_no in range(max(1, class_start - 8), class_end + 1):
        line = lines[line_no - 1]
        stripped = line.strip()
        context_lines.append(line)
        if "{" in stripped:
            break
    return "\n".join(context_lines)


def _java_class_end(lines: list[str], class_start: int) -> int:
    return _brace_block_end(lines, class_start)


def _java_member_end(lines: list[str], member_start: int) -> int:
    return _brace_block_end(lines, member_start)


def _brace_block_end(lines: list[str], start: int) -> int:
    depth = 0
    seen_open = False
    for index in range(start - 1, len(lines)):
        line = lines[index]
        for char in line:
            if char == "{":
                depth += 1
                seen_open = True
            elif char == "}":
                depth -= 1
                if seen_open and depth <= 0:
                    return index + 1
    return len(lines)


def _node_start(node: ast.AST) -> int:
    decorators = getattr(node, "decorator_list", []) or []
    starts = [getattr(node, "lineno", 1)]
    starts.extend(getattr(decorator, "lineno", starts[0]) for decorator in decorators)
    return min(starts)


def _node_end(node: ast.AST) -> int:
    return int(getattr(node, "end_lineno", getattr(node, "lineno", 1)))


def _line(node: Any) -> int:
    position = getattr(node, "position", None)
    return int(position.line) if position else 1


def _slice_lines(lines: list[str], start: int, end: int) -> str:
    if end < start or not lines:
        return ""
    start = max(start, 1)
    end = min(end, len(lines))
    return "\n".join(lines[start - 1 : end])


def _join_parts(*parts: str) -> str:
    return "\n\n".join(part.strip("\n") for part in parts if part and part.strip())


def _store_matches_current_strategy(store: FaissVectorStore) -> bool:
    if not store.records:
        return False
    return all(
        item.get("index_version") == INDEX_VERSION and item.get("chunk_strategy") == CHUNK_STRATEGY
        for item in store.records
    )


def _should_skip(path: Path, repo: Path) -> bool:
    try:
        rel_parts = path.relative_to(repo).parts
    except ValueError:
        return True
    return any(part in SKIP_DIRS for part in rel_parts)


def _stable_id(relative_path: str, chunk_no: int, chunk: str) -> str:
    digest = hashlib.sha1(f"{relative_path}:{chunk_no}:{chunk}".encode("utf-8")).hexdigest()[:12]
    return f"{relative_path}:{chunk_no}:{digest}"
