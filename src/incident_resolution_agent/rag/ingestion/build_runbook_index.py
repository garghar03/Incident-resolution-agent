from pathlib import Path
from typing import List

def build_runbook_index(source_dir: str, out_dir: str):
    # Lightweight placeholder that copies runbooks (markdown) into an index
    src = Path(source_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    runbooks: List[Path] = list(src.rglob("*.md"))

    for rb in runbooks:
        target = out / rb.name
        target.write_text(rb.read_text(encoding="utf-8"), encoding="utf-8")

    return len(runbooks)
