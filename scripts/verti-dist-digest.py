import hashlib
from pathlib import Path

root = Path("dist")
paths = sorted(root.rglob("*"), key=lambda path: path.relative_to(root).as_posix())
h = hashlib.sha256()
for p in paths:
    if p.is_symlink():
        raise SystemExit(f"Unexpected symlink: {p}")
    if p.is_file():
        rel = p.relative_to(root).as_posix()
        if any(part.startswith(".") for part in Path(rel).parts):
            raise SystemExit(f"Unexpected hidden file: {p}")
        h.update(rel.encode("utf-8") + b"\0" + hashlib.sha256(p.read_bytes()).digest())
assert (root / "index.html").stat().st_size > 0
assert (root / "en/index.html").stat().st_size > 0
print(h.hexdigest())
