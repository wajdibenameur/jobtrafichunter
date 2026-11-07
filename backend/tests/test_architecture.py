"""Enforce module public boundaries without a new runtime dependency."""

import ast
from pathlib import Path

ROOT = Path(__file__).parents[1] / "app"
ALLOWED = {
    "auth": set(),
    "cv": set(),
    "ai": set(),
    "sources": set(),
    "listings": set(),
    "profile": {"cv", "ai"},
    "matching": {"profile", "ai"},
    "notifications": set(),
    "applications": {"listings"},
    "search": {"sources", "listings", "matching", "notifications", "profile"},
}


def test_module_boundaries_and_dependency_direction() -> None:
    violations = []
    for file in ROOT.rglob("*.py"):
        relative = file.relative_to(ROOT)
        if "tests" in relative.parts:
            continue
        module = relative.parts[1] if relative.parts[0] == "modules" else None
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            imports = []
            if isinstance(node, ast.ImportFrom):
                assert not node.level, f"Use absolute imports for enforceable boundaries: {file}"
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            for name in imports:
                parts = name.split(".")
                if parts[:2] != ["app", "modules"]:
                    continue
                if relative.parts[0] in {"core", "shared"}:
                    violations.append(f"{relative}: infrastructure depends on {name}")
                if len(parts) >= 3 and parts[2] != module:
                    if len(parts) != 3:
                        violations.append(f"{relative}: private module import {name}")
                    if module is not None and parts[2] not in ALLOWED[module]:
                        violations.append(f"{relative}: forbidden dependency {name}")
    assert not violations, "\n".join(violations)
