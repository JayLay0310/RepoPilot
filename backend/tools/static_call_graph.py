import ast
import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from backend.utils.helpers import is_text_file

try:
    import javalang
except Exception:  # pragma: no cover
    javalang = None

SKIP_DIRS = {".git", ".idea", ".venv", "__pycache__", "node_modules", ".faiss", ".cache", "dist", "build"}
CACHE_VERSION = 4
SPRING_COMPONENT_ANNOTATIONS = {"Component", "Service", "Repository", "Controller", "RestController", "Configuration"}
SPRING_ROUTE_ANNOTATIONS = {"RequestMapping", "GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping"}
INJECTION_ANNOTATIONS = {"Autowired", "Resource", "Inject"}


def build_static_call_graph(repo_path: str, force_rebuild: bool = False) -> dict[str, Any]:
    repo = Path(repo_path).resolve()
    files = _source_files(repo)
    fingerprint = _fingerprint(files)
    cache_path = _cache_path(repo)

    if not force_rebuild:
        cached = _load_cache(cache_path, fingerprint)
        if cached is not None:
            cached["stats"]["cache"] = "hit"
            return cached

    previous = None if force_rebuild else _load_cache(cache_path, None)
    graph = _build_graph(repo, files, previous)
    graph["fingerprint"] = fingerprint
    graph["cache_version"] = CACHE_VERSION
    graph["stats"]["cache"] = "miss"
    _save_cache(cache_path, graph)
    return graph


def trace_static_call_chain(repo_path: str, symbol: str, max_depth: int = 3) -> dict[str, Any]:
    graph = build_static_call_graph(repo_path)
    starts = _resolve_symbol(symbol, _index_graph_nodes(graph["nodes"]))
    if not starts:
        starts = [node["id"] for node in graph["nodes"] if symbol.lower() in node["id"].lower()]

    adjacency = graph["adjacency"]
    visited = set(starts)
    queue = deque((start, 0) for start in starts)
    chain_edges = []

    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for target in adjacency.get(current, []):
            chain_edges.append({"from": current, "to": target, "depth": depth + 1})
            if target not in visited:
                visited.add(target)
                queue.append((target, depth + 1))

    return {
        "symbol": symbol,
        "resolved_symbols": starts,
        "chain": chain_edges,
        "nodes": [node for node in graph["nodes"] if node["id"] in visited],
        "entrypoints": _entrypoints_for_symbols(graph, starts),
        "stats": graph["stats"],
    }


def _build_graph(repo: Path, files: list[Path], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    symbol_index: dict[str, set[str]] = defaultdict(set)
    python_units: dict[str, dict[str, Any]] = {}
    java_units: dict[str, dict[str, Any]] = {}
    previous_units = (previous or {}).get("file_units", {})
    file_units: dict[str, dict[str, Any]] = {}
    parsed_files = 0
    reused_files = 0

    for path in files:
        file_key = str(path)
        file_sig = _file_signature(path)
        cached_unit = previous_units.get(file_key)
        if cached_unit and cached_unit.get("signature") == file_sig:
            unit = cached_unit["unit"]
            reused_files += 1
        elif path.suffix == ".py":
            unit = _parse_python_unit(repo, path)
            parsed_files += 1
        elif path.suffix == ".java":
            unit = _parse_java_unit(repo, path)
            parsed_files += 1
        else:
            continue

        file_units[file_key] = {"signature": file_sig, "unit": unit}
        if path.suffix == ".py":
            python_units[str(path)] = unit
            _register_nodes(unit["nodes"], nodes, symbol_index)
        elif path.suffix == ".java":
            java_units[str(path)] = unit
            _register_nodes(unit["nodes"], nodes, symbol_index)

    for unit in python_units.values():
        unit_edges, unit_unresolved = _resolve_python_calls(unit, symbol_index)
        edges.extend(unit_edges)
        unresolved.extend(unit_unresolved)

    java_class_index = _java_class_index(java_units)
    java_bean_index = _java_bean_index(java_units)
    for unit in java_units.values():
        unit_edges, unit_unresolved = _resolve_java_calls(unit, symbol_index, java_class_index, java_bean_index)
        edges.extend(unit_edges)
        unresolved.extend(unit_unresolved)

    deduped_edges, adjacency, reverse_adjacency = _dedupe_edges(edges)
    spring_entrypoints = _spring_entrypoints(java_units)
    fastapi_entrypoints = _fastapi_entrypoints(nodes)
    bean_dependencies = _spring_bean_dependencies(java_units, java_class_index, java_bean_index)

    return {
        "nodes": sorted(nodes.values(), key=lambda item: item["id"]),
        "edges": sorted(deduped_edges, key=lambda item: (item["from"], item["to"], item.get("line", 0))),
        "adjacency": adjacency,
        "reverse_adjacency": reverse_adjacency,
        "unresolved_calls": unresolved,
        "spring": {
            "entrypoints": spring_entrypoints,
            "bean_dependencies": bean_dependencies,
        },
        "fastapi": {
            "entrypoints": fastapi_entrypoints,
        },
        "file_units": file_units,
        "stats": {
            "files": len(files),
            "parsed_files": parsed_files,
            "reused_files": reused_files,
            "nodes": len(nodes),
            "edges": len(deduped_edges),
            "unresolved_calls": len(unresolved),
            "spring_entrypoints": len(spring_entrypoints),
            "fastapi_entrypoints": len(fastapi_entrypoints),
            "bean_dependencies": len(bean_dependencies),
        },
    }


def _parse_python_unit(repo: Path, path: Path) -> dict[str, Any]:
    module = ".".join(path.relative_to(repo).with_suffix("").parts)
    code = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"language": "python", "path": str(path), "module": module, "nodes": [], "calls": [], "imports": {}, "local_symbols": {}}

    nodes = []
    calls = []
    imports = _python_imports(tree)
    local_symbols: dict[str, str] = {}

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node_id = f"{module}.{node.name}"
            routes = _fastapi_routes(node)
            nodes.append(
                _node(
                    node_id,
                    node.name,
                    str(path),
                    node.lineno,
                    "python",
                    "function",
                    role="endpoint" if routes else None,
                    routes=routes,
                )
            )
            local_symbols[node.name] = node_id
            calls.extend(_python_calls(node, node_id, module, None))
        elif isinstance(node, ast.ClassDef):
            class_id = f"{module}.{node.name}"
            nodes.append(_node(class_id, node.name, str(path), node.lineno, "python", "class"))
            local_symbols[node.name] = class_id
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_id = f"{class_id}.{child.name}"
                    routes = _fastapi_routes(child)
                    nodes.append(
                        _node(
                            method_id,
                            child.name,
                            str(path),
                            child.lineno,
                            "python",
                            "method",
                            owner=class_id,
                            role="endpoint" if routes else None,
                            routes=routes,
                        )
                    )
                    local_symbols[child.name] = method_id
                    calls.extend(_python_calls(child, method_id, module, class_id))

    return {
        "language": "python",
        "path": str(path),
        "module": module,
        "nodes": nodes,
        "calls": calls,
        "imports": imports,
        "local_symbols": local_symbols,
    }


def _python_imports(tree: ast.Module) -> dict[str, str]:
    imports = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imports[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return imports


def _python_calls(func_node: ast.AST, caller: str, module: str, current_class: str | None) -> list[dict[str, Any]]:
    calls = []
    for child in ast.walk(func_node):
        if not isinstance(child, ast.Call):
            continue
        name, qualifier, kind = _python_call_name(child.func)
        if not name:
            continue
        calls.append(
            {
                "from": caller,
                "name": name,
                "qualifier": qualifier,
                "kind": kind,
                "line": getattr(child, "lineno", 0),
                "module": module,
                "current_class": current_class,
            }
        )
        if name == "add_task" and child.args:
            task_target = child.args[0]
            if isinstance(task_target, ast.Name):
                calls.append(
                    {
                        "from": caller,
                        "name": task_target.id,
                        "qualifier": None,
                        "kind": "function_reference",
                        "line": getattr(child, "lineno", 0),
                        "module": module,
                        "current_class": current_class,
                    }
                )
    return calls


def _resolve_python_calls(unit: dict[str, Any], symbol_index: dict[str, set[str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    edges = []
    unresolved = []
    imports = unit.get("imports", {})

    for call in unit["calls"]:
        candidates = []
        qualifier = call.get("qualifier")
        if call["kind"] == "self_attribute" and call["current_class"]:
            candidates = [f"{call['current_class']}.{call['name']}"]
        elif qualifier and qualifier in imports:
            candidates = _resolve_symbol(f"{imports[qualifier]}.{call['name']}", symbol_index)
        elif call["name"] in imports:
            candidates = _resolve_symbol(imports[call["name"]], symbol_index)
        elif call["name"] in unit.get("local_symbols", {}):
            candidates = [unit["local_symbols"][call["name"]]]
        else:
            candidates = _resolve_symbol(call["name"], symbol_index)

        targets = [candidate for candidate in candidates if candidate in _all_symbol_ids(symbol_index)]
        if targets:
            for target in targets:
                edges.append(_edge(call["from"], target, call["line"], call["name"], "python-ast"))
        else:
            unresolved.append({**call, "reason": "no matching definition"})
    return edges, unresolved


def _parse_java_unit(repo: Path, path: Path) -> dict[str, Any]:
    code = path.read_text(encoding="utf-8", errors="ignore")
    empty = {"language": "java", "path": str(path), "nodes": [], "calls": [], "classes": {}, "package": "", "imports": {}}
    if javalang is None:
        return empty

    try:
        tree = javalang.parse.parse(code)
    except Exception:
        return empty

    nodes = []
    calls = []
    classes = {}
    package = tree.package.name if tree.package else ""
    imports = {item.path.rsplit(".", 1)[-1]: item.path for item in tree.imports}

    for _, class_node in tree.filter(javalang.tree.ClassDeclaration):
        class_name = class_node.name
        class_id = f"{package}.{class_name}" if package else class_name
        annotations = _annotations(class_node)
        role = _spring_role(annotations, class_name)
        class_routes = _route_paths(class_node)
        nodes.append(_node(class_id, class_name, str(path), _line(class_node), "java", "class", role=role, annotations=annotations))

        fields = _java_fields(class_node)
        injected_fields = _java_injected_fields(class_node)
        classes[class_name] = {
            "id": class_id,
            "fields": fields,
            "injected_fields": injected_fields,
            "imports": imports,
            "package": package,
            "role": role,
            "annotations": sorted(annotations),
        }

        for method in class_node.methods:
            method_id = f"{class_id}.{method.name}"
            method_annotations = _annotations(method)
            route_paths = _join_routes(class_routes, _route_paths(method))
            nodes.append(
                _node(
                    method_id,
                    method.name,
                    str(path),
                    _line(method),
                    "java",
                    "method",
                    owner=class_id,
                    role="endpoint" if route_paths else None,
                    annotations=method_annotations,
                    routes=route_paths,
                )
            )
            calls.extend(_java_method_calls(method, method_id, class_name, class_id, {**fields, **injected_fields}))

        for constructor in class_node.constructors:
            method_id = f"{class_id}.{constructor.name}"
            nodes.append(_node(method_id, constructor.name, str(path), _line(constructor), "java", "constructor", owner=class_id))
            constructor_fields = dict(fields)
            for parameter in getattr(constructor, "parameters", []) or []:
                constructor_fields[parameter.name] = _java_type_name(parameter.type)
            calls.extend(_java_method_calls(constructor, method_id, class_name, class_id, constructor_fields))

    return {"language": "java", "path": str(path), "nodes": nodes, "calls": calls, "classes": classes, "package": package, "imports": imports}


def _resolve_java_calls(
    unit: dict[str, Any],
    symbol_index: dict[str, set[str]],
    class_index: dict[str, str],
    bean_index: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    edges = []
    unresolved = []
    for call in unit["calls"]:
        targets = []
        qualifier = call.get("qualifier")
        if qualifier:
            target_class = (
                call["variables"].get(qualifier)
                or bean_index.get(qualifier)
                or class_index.get(qualifier)
                or unit.get("imports", {}).get(qualifier)
            )
            if target_class:
                target_class_id = class_index.get(target_class, target_class)
                targets = _resolve_symbol(f"{target_class_id}.{call['name']}", symbol_index)
        if not targets:
            targets = _resolve_symbol(f"{call['current_class_id']}.{call['name']}", symbol_index)
        if not targets:
            targets = _resolve_symbol(call["name"], symbol_index)

        if targets:
            for target in targets:
                edges.append(_edge(call["from"], target, call["line"], call["name"], "javalang"))
        else:
            unresolved.append({**call, "reason": "no matching definition"})
    return edges, unresolved


def _java_method_calls(method: Any, caller: str, class_name: str, class_id: str, fields: dict[str, str]) -> list[dict[str, Any]]:
    variables = dict(fields)
    for parameter in getattr(method, "parameters", []) or []:
        variables[parameter.name] = _java_type_name(parameter.type)
    for _, local in method.filter(javalang.tree.LocalVariableDeclaration):
        type_name = _java_type_name(local.type)
        for declarator in local.declarators:
            variables[declarator.name] = type_name

    calls = []
    for _, invocation in method.filter(javalang.tree.MethodInvocation):
        calls.append(
            {
                "from": caller,
                "name": invocation.member,
                "qualifier": invocation.qualifier,
                "line": _line(invocation),
                "class_name": class_name,
                "current_class_id": class_id,
                "variables": variables,
            }
        )
    return calls


def _java_fields(class_node: Any) -> dict[str, str]:
    fields = {}
    for field in class_node.fields:
        type_name = _java_type_name(field.type)
        for declarator in field.declarators:
            fields[declarator.name] = type_name
    return fields


def _java_injected_fields(class_node: Any) -> dict[str, str]:
    injected = {}
    for field in class_node.fields:
        annotations = _annotations(field)
        if not annotations.intersection(INJECTION_ANNOTATIONS):
            continue
        type_name = _java_type_name(field.type)
        for declarator in field.declarators:
            injected[declarator.name] = type_name
    return injected


def _spring_bean_dependencies(java_units: dict[str, dict[str, Any]], class_index: dict[str, str], bean_index: dict[str, str]) -> list[dict[str, Any]]:
    dependencies = []
    for unit in java_units.values():
        for meta in unit.get("classes", {}).values():
            source = meta["id"]
            for field, type_name in meta.get("injected_fields", {}).items():
                target = class_index.get(type_name) or bean_index.get(field)
                if target:
                    dependencies.append({"from": source, "to": target, "field": field, "type": type_name})
    return dependencies


def _spring_entrypoints(java_units: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    entrypoints = []
    for unit in java_units.values():
        for node in unit.get("nodes", []):
            for route in node.get("routes", []) or []:
                entrypoints.append(
                    {
                        "method": route["http_method"],
                        "path": route["path"],
                        "handler": node["id"],
                        "file": node["path"],
                        "line": node["line"],
                    }
                )
    return entrypoints


def _fastapi_entrypoints(nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    entrypoints = []
    for node in nodes.values():
        if node.get("language") != "python":
            continue
        for route in node.get("routes", []) or []:
            entrypoints.append(
                {
                    "method": route["http_method"],
                    "path": route["path"],
                    "handler": node["id"],
                    "file": node["path"],
                    "line": node["line"],
                    "framework": "fastapi",
                }
            )
    return entrypoints


def _entrypoints_for_symbols(graph: dict[str, Any], symbols: list[str]) -> list[dict[str, Any]]:
    reverse = graph.get("reverse_adjacency", {})
    found = []
    entrypoints = []
    entrypoints.extend(graph.get("spring", {}).get("entrypoints", []))
    entrypoints.extend(graph.get("fastapi", {}).get("entrypoints", []))
    for entrypoint in entrypoints:
        handler = entrypoint["handler"]
        if handler in symbols or any(handler in _reachable_reverse(symbol, reverse, max_depth=4) for symbol in symbols):
            found.append(entrypoint)
    return found


def _reachable_reverse(start: str, reverse: dict[str, list[str]], max_depth: int) -> set[str]:
    visited = {start}
    queue = deque([(start, 0)])
    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for parent in reverse.get(current, []):
            if parent not in visited:
                visited.add(parent)
                queue.append((parent, depth + 1))
    return visited


def _java_class_index(java_units: dict[str, dict[str, Any]]) -> dict[str, str]:
    index = {}
    for unit in java_units.values():
        for class_name, meta in unit.get("classes", {}).items():
            index[class_name] = meta["id"]
            index[meta["id"]] = meta["id"]
    return index


def _java_bean_index(java_units: dict[str, dict[str, Any]]) -> dict[str, str]:
    index = {}
    for unit in java_units.values():
        for class_name, meta in unit.get("classes", {}).items():
            if meta.get("role"):
                index[_lower_camel(class_name)] = meta["id"]
                index[class_name] = meta["id"]
    return index


def _dedupe_edges(edges: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, list[str]]]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    reverse_adjacency: dict[str, list[str]] = defaultdict(list)
    seen_edges = set()
    deduped_edges = []
    for edge in edges:
        key = (edge["from"], edge["to"], edge.get("line"))
        if key in seen_edges:
            continue
        seen_edges.add(key)
        deduped_edges.append(edge)
        adjacency[edge["from"]].append(edge["to"])
        reverse_adjacency[edge["to"]].append(edge["from"])
    return (
        deduped_edges,
        {key: sorted(set(value)) for key, value in adjacency.items()},
        {key: sorted(set(value)) for key, value in reverse_adjacency.items()},
    )


def _source_files(repo: Path) -> list[Path]:
    return [
        path
        for path in repo.rglob("*")
        if path.is_file() and not _should_skip(path, repo) and path.suffix in {".py", ".java"} and is_text_file(path)
    ]


def _fingerprint(files: list[Path]) -> str:
    payload = [
        f"{path}:{path.stat().st_mtime_ns}:{path.stat().st_size}"
        for path in sorted(files, key=lambda item: str(item))
    ]
    return hashlib.sha256("\n".join(payload).encode("utf-8")).hexdigest()


def _cache_path(repo: Path) -> Path:
    cache_dir = repo / ".faiss"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "call_graph.json"


def _load_cache(cache_path: Path, fingerprint: str | None) -> dict[str, Any] | None:
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if payload.get("cache_version") != CACHE_VERSION:
        return None
    if fingerprint is not None and payload.get("fingerprint") != fingerprint:
        return None
    return payload


def _save_cache(cache_path: Path, graph: dict[str, Any]) -> None:
    cache_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")


def _file_signature(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {"mtime_ns": stat.st_mtime_ns, "size": stat.st_size}


def _register_nodes(nodes: list[dict[str, Any]], registry: dict[str, dict[str, Any]], symbol_index: dict[str, set[str]]) -> None:
    for item in nodes:
        registry[item["id"]] = item
        for key in {item["id"], item["name"], item["id"].rsplit(".", 1)[-1]}:
            symbol_index[key].add(item["id"])


def _index_graph_nodes(nodes: list[dict[str, Any]]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for item in nodes:
        for key in {item["id"], item["name"], item["id"].rsplit(".", 1)[-1]}:
            index[key].add(item["id"])
    return index


def _resolve_symbol(symbol: str, symbol_index: dict[str, set[str]]) -> list[str]:
    if symbol in symbol_index:
        return sorted(symbol_index[symbol])
    suffix_matches = []
    for key, values in symbol_index.items():
        if key.endswith(f".{symbol}") or any(value.endswith(f".{symbol}") for value in values):
            suffix_matches.extend(values)
    return sorted(set(suffix_matches))


def _all_symbol_ids(symbol_index: dict[str, set[str]]) -> set[str]:
    values = set()
    for ids in symbol_index.values():
        values.update(ids)
    return values


def _python_call_name(func: ast.AST) -> tuple[str | None, str | None, str]:
    if isinstance(func, ast.Name):
        return func.id, None, "name"
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            if func.value.id in {"self", "cls"}:
                return func.attr, func.value.id, "self_attribute"
            return func.attr, func.value.id, "attribute"
        return func.attr, None, "attribute"
    return None, None, "unknown"


def _fastapi_routes(func_node: ast.AST) -> list[dict[str, str]]:
    routes = []
    for decorator in getattr(func_node, "decorator_list", []) or []:
        call = decorator if isinstance(decorator, ast.Call) else None
        target = call.func if call is not None else decorator
        if not isinstance(target, ast.Attribute):
            continue
        http_method = target.attr.upper()
        if http_method not in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD", "WEBSOCKET"}:
            continue
        qualifier = target.value.id if isinstance(target.value, ast.Name) else ""
        if qualifier not in {"app", "router", "api", "bp"} and not qualifier.endswith("router"):
            continue
        path = ""
        if call is not None and call.args:
            path = _literal_string(call.args[0])
        if not path and call is not None:
            for keyword in call.keywords:
                if keyword.arg in {"path", "url_path"}:
                    path = _literal_string(keyword.value)
                    break
        routes.append({"http_method": "WS" if http_method == "WEBSOCKET" else http_method, "path": path})
    return routes


def _literal_string(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Str):
        return node.s
    return ""


def _annotations(node: Any) -> set[str]:
    return {annotation.name.split(".")[-1] for annotation in getattr(node, "annotations", []) or []}


def _spring_role(annotations: set[str], class_name: str) -> str | None:
    matched = annotations.intersection(SPRING_COMPONENT_ANNOTATIONS)
    if matched:
        return sorted(matched)[0].lower()
    lowered = class_name.lower()
    for suffix in ("controller", "service", "repository", "mapper"):
        if lowered.endswith(suffix):
            return suffix
    return None


def _route_paths(node: Any) -> list[dict[str, str]]:
    routes = []
    for annotation in getattr(node, "annotations", []) or []:
        name = annotation.name.split(".")[-1]
        if name in SPRING_ROUTE_ANNOTATIONS:
            routes.append({"http_method": _http_method(name, annotation), "path": _annotation_path(annotation)})
    return routes


def _join_routes(class_routes: list[dict[str, str]], method_routes: list[dict[str, str]]) -> list[dict[str, str]]:
    if not method_routes:
        return []
    if not class_routes:
        return method_routes
    joined = []
    for class_route in class_routes:
        for method_route in method_routes:
            joined.append(
                {
                    "http_method": method_route["http_method"] if method_route["http_method"] != "ANY" else class_route["http_method"],
                    "path": f"{class_route['path']}{method_route['path']}",
                }
            )
    return joined


def _http_method(annotation: str, annotation_node: Any | None = None) -> str:
    mapped = {
        "GetMapping": "GET",
        "PostMapping": "POST",
        "PutMapping": "PUT",
        "DeleteMapping": "DELETE",
        "PatchMapping": "PATCH",
    }.get(annotation)
    if mapped:
        return mapped
    values = " ".join(_annotation_values(annotation_node)) if annotation_node is not None else ""
    for method in ("GET", "POST", "PUT", "DELETE", "PATCH"):
        if method in values:
            return method
    return "ANY"


def _annotation_path(annotation: Any) -> str:
    for value in _annotation_values(annotation):
        if value.startswith("/"):
            return value
    return ""


def _annotation_values(annotation: Any) -> list[str]:
    element = getattr(annotation, "element", None)
    return [_clean_annotation_value(value) for value in _walk_annotation_values(element) if _clean_annotation_value(value)]


def _walk_annotation_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        values = []
        for item in value:
            values.extend(_walk_annotation_values(item))
        return values
    if hasattr(value, "value"):
        return _walk_annotation_values(value.value)
    if hasattr(value, "values"):
        return _walk_annotation_values(value.values)
    if hasattr(value, "name") and hasattr(value, "value"):
        return _walk_annotation_values(value.value)
    return [value]


def _clean_annotation_value(value: Any) -> str:
    text = str(value).strip()
    if "=" in text and "value=" in text:
        text = text.split("value=", 1)[-1].split(",", 1)[0].strip(" )")
    return text.strip('"').strip("'")


def _node(
    node_id: str,
    name: str,
    path: str,
    line: int,
    language: str,
    kind: str,
    owner: str | None = None,
    role: str | None = None,
    annotations: set[str] | None = None,
    routes: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "name": name,
        "path": path,
        "line": line,
        "language": language,
        "kind": kind,
        "owner": owner,
        "role": role,
        "annotations": sorted(annotations or []),
        "routes": routes or [],
    }


def _edge(source: str, target: str, line: int, call: str, resolver: str) -> dict[str, Any]:
    return {"from": source, "to": target, "line": line, "call": call, "resolver": resolver}


def _java_type_name(type_node: Any) -> str:
    if type_node is None:
        return ""
    return getattr(type_node, "name", str(type_node))


def _line(node: Any) -> int:
    position = getattr(node, "position", None)
    return int(position.line) if position else 0


def _lower_camel(name: str) -> str:
    return name[:1].lower() + name[1:] if name else name


def _should_skip(path: Path, repo: Path) -> bool:
    try:
        rel_parts = path.relative_to(repo).parts
    except ValueError:
        return True
    return any(part in SKIP_DIRS for part in rel_parts)
