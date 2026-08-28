"""Move TODO items to DONE whole. Usage: move_done.py <heading> <note-file> <prefix> [<prefix> ...]"""
import sys
from pathlib import Path

root = Path(r"C:\Users\nbasl\OneDrive\Documents\vs-code-repos\black_bot_baf\docs")
todo = root / "TODO.md"
done = root / "DONE.md"

heading, note_file, *prefixes = sys.argv[1:]
note = Path(note_file).read_text(encoding="utf-8").strip()

lines = todo.read_text(encoding="utf-8").splitlines(keepends=True)
moved = []
for prefix in prefixes:
    idx = next(i for i, l in enumerate(lines) if l.startswith(prefix))
    moved.append(lines.pop(idx))
    if idx > 0 and lines[idx - 1].strip() == "" and idx < len(lines) and lines[idx].strip() == "":
        lines.pop(idx)
todo.write_text("".join(lines), encoding="utf-8")

entry = f"## {heading}\n\nMoved whole from `TODO.md`:\n\n" + "".join(moved) + "\n" + note + "\n\n"
text = done.read_text(encoding="utf-8")
first = text.index("\n## ")
done.write_text(text[: first + 1] + entry + text[first + 1 :], encoding="utf-8")
print("moved", len(moved))
