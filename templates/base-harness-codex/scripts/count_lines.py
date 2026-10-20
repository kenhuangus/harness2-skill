import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: count_lines.py <file>")
        return 2
    lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    print(f"Lines: {len(lines)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
