import ast
from pathlib import Path

EXCLUDED_DIRS = {"venv", ".venv", "env", ".env", "__pycache__", "site-packages", "future"}
CAUGHT_VIOLATIONS_EXAMPLE = """
FOO = str | None

class Foo:
    a: str | None

    def bar(self, baz: str | None) -> str | None:
        foo: str | None = None
        bar: FOO = None
        return foo

def baz(foo: str | None) -> str | None:
    return None
"""


class UnionPipeChecker(ast.NodeVisitor):
    def __init__(self, filename: str, violations: list[str]):
        self.filename = filename
        self.violations = violations

    def visit_Assign(self, node):
        if isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.BitOr):
            self.violations.append(
                f"{self.filename}:{node.lineno}:{node.col_offset} - '|' used in type alias (Assign)"
            )
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if self._contains_bitwise_or(node.annotation):
            self.violations.append(
                f"{self.filename}:{node.lineno}:{node.col_offset} - '|' used in type annotation"
            )
        self.generic_visit(node)

    def visit_arg(self, node):
        if node.annotation and self._contains_bitwise_or(node.annotation):
            self.violations.append(
                f"{self.filename}:{node.lineno}:{node.col_offset} - '|' used in function argument annotation"
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.returns and self._contains_bitwise_or(node.returns):
            self.violations.append(
                f"{self.filename}:{node.lineno}:{node.col_offset} - '|' used in return type annotation"
            )
        self.generic_visit(node)

    def _contains_bitwise_or(self, node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return True
        for child in ast.iter_child_nodes(node):
            if self._contains_bitwise_or(child):
                return True
        return False


def check_file(filepath: Path, violations: list[str]):
    try:
        with filepath.open("r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(filepath))
        checker = UnionPipeChecker(str(filepath), violations)
        checker.visit(tree)
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"{filepath}: Skipped due to parsing error ({e.__class__.__name__})")


def should_exclude(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def test_union_pipe_checker():
    filename = "test"
    violations = []
    tree = ast.parse(CAUGHT_VIOLATIONS_EXAMPLE, filename=filename)

    checker = UnionPipeChecker(filename, violations)

    checker.visit(tree)
    assert len(violations) == 7


def test_no_union_pipe_operators_present_in_types():
    violations = []
    for filepath in Path(".").rglob("*.py"):
        if should_exclude(filepath):
            continue
        check_file(filepath, violations)

    for violation in violations:
        print(violation)
    assert not violations
