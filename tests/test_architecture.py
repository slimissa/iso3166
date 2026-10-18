import ast
from pathlib import Path
import pytest

SCRIPT_PATH = Path("tools/export_aggregated.py")

class ArchitectureVisitor(ast.NodeVisitor):
    """
    Parses the AST of export_aggregated.py to enforce the Medallion rule:
    The AGGREGATED layer must never read from the RAW layer (JSON).
    """
    def __init__(self):
        self.violations = []

    def _record_violation(self, node: ast.AST, message: str):
        lineno = getattr(node, "lineno", "unknown")
        self.violations.append(f"Line {lineno}: {message}")

    def visit_Module(self, node: ast.Module):
        # Skip the module-level docstring to avoid self-triggering
        start_idx = 0
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            if isinstance(node.body[0].value.value, str):
                start_idx = 1
        
        for stmt in node.body[start_idx:]:
            self.visit(stmt)

    def visit_Constant(self, node: ast.Constant):
        # Catch ANY string literal ending in .json
        if isinstance(node.value, str):
            if node.value.endswith(".json") or "iso3166.json" in node.value:
                self._record_violation(node, f"Found string literal accessing RAW layer: {node.value!r}")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        # Catch `import json` and `import json as j`
        for alias in node.names:
            if alias.name == "json" or alias.name.startswith("json."):
                self._record_violation(node, f"Found illegal import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # Catch `from json import loads`
        if node.module and (node.module == "json" or node.module.startswith("json.")):
            self._record_violation(node, f"Found illegal import from: {node.module}")
        self.generic_visit(node)


def test_aggregated_layer_does_not_read_raw():
    """
    Enforce Medallion Architecture: AGGREGATED must not read RAW.
    We parse the AST to ensure no `json` imports and no `.json` file access.
    """
    assert SCRIPT_PATH.exists(), f"Script not found: {SCRIPT_PATH}"
    
    source_code = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source_code)
    
    visitor = ArchitectureVisitor()
    visitor.visit(tree)
    
    if visitor.violations:
        error_msg = "ARCHITECTURE VIOLATION: AGGREGATED layer attempted to access RAW layer.\n"
        error_msg += "\n".join(visitor.violations)
        error_msg += "\n\nRule: tools/export_aggregated.py must only read from iso3166.parquet."
        pytest.fail(error_msg)


def test_architecture_visitor_catches_violations():
    """
    Meta-test: Ensure the AST visitor actually works by feeding it bad code.
    """
    bad_code = """
import json
from pathlib import Path

def bad_function():
    with open("iso3166.json") as f:
        pass
    p = Path("data.json")
    print("This is fine")
"""
    tree = ast.parse(bad_code)
    visitor = ArchitectureVisitor()
    visitor.visit(tree)
    
    # Expect 3 violations: import json, open("iso3166.json"), Path("data.json")
    assert len(visitor.violations) == 3, f"Expected 3 violations, got: {visitor.violations}"
    
    # Ensure it allows safe code
    good_code = """
from pathlib import Path

def good_function():
    p = Path("iso3166.parquet")
    print("This is fine")
"""
    tree_good = ast.parse(good_code)
    visitor_good = ArchitectureVisitor()
    visitor_good.visit(tree_good)
    assert len(visitor_good.violations) == 0, "Visitor falsely flagged safe code"