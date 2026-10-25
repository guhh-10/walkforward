import ast
from pathlib import Path

ML_DIR = Path(__file__).resolve().parents[1] / "app" / "ml"
FORBIDDEN = (
    "app.api",
    "app.services",
    "app.repositories",
    "app.models",
    "app.database",
    "app.schemas",
    "sqlalchemy",
    "fastapi",
)


def imported_modules(path: Path) -> list[str]:
    modules: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def test_ml_package_does_not_depend_on_app_layers_or_frameworks() -> None:
    files = sorted(ML_DIR.glob("*.py"))
    assert files, "expected app/ml to contain modules"
    for path in files:
        for module in imported_modules(path):
            assert not module.startswith(FORBIDDEN), f"{path.name} imports {module}"
