def build_markdown_report(sections: dict[str, str], title: str = "RepoPilot Analysis Report") -> str:
    lines = [f"# {title}", ""]
    for name, content in sections.items():
        lines.extend([f"## {name}", "", content.strip(), ""])
    return "\n".join(lines).strip() + "\n"
