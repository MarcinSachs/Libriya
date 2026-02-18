import ast
import glob
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
VERSIONS = os.path.join(ROOT, 'migrations', 'versions')


def parse_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()

    rev = None
    down = None

    for line in src.splitlines():
        line = line.strip()
        if line.startswith('revision') and '=' in line:
            try:
                rev = ast.literal_eval(line.split('=', 1)[1].strip())
            except Exception:
                pass
        if line.startswith('down_revision') and '=' in line:
            rhs = line.split('=', 1)[1].strip()
            try:
                down = ast.literal_eval(rhs)
            except Exception:
                # try to handle tuple across multiple lines
                # fallback: search for a bracketed tuple in the file
                import re
                m = re.search(r"down_revision\s*=\s*\((.*?)\)", src, re.S)
                if m:
                    txt = '(' + m.group(1) + ')'
                    try:
                        down = ast.literal_eval(txt)
                    except Exception:
                        down = None
                else:
                    # try single string
                    m2 = re.search(r"down_revision\s*=\s*['\"]([^'\"]+)['\"]", src)
                    if m2:
                        down = m2.group(1)
    return rev, down


def main():
    files = sorted(glob.glob(os.path.join(VERSIONS, '*.py')))
    rev_map = {}
    down_map = {}

    for p in files:
        rev, down = parse_file(p)
        name = os.path.relpath(p)
        if rev is None:
            print(f"WARN: no revision found in {name}")
            continue
        if rev in rev_map:
            print(f"ERROR: duplicate revision {rev} in {name} and {rev_map[rev]}")
        rev_map[rev] = name
        if down is None:
            down_map[rev] = []
        elif isinstance(down, (list, tuple)):
            down_map[rev] = list(down)
        else:
            down_map[rev] = [down]

    known = set(rev_map.keys())

    print(f"Found {len(rev_map)} revisions.")

    missing = set()
    for rev, downs in down_map.items():
        for d in downs:
            if d is None:
                continue
            if d not in known:
                missing.add((rev, d))

    if missing:
        print("Missing down_revision references:")
        for rev, d in sorted(missing):
            print(f"  {rev} -> {d} (referenced by {down_map.get(rev)})")
    else:
        print("All down_revision references resolved.")

    # find heads (revisions not referenced by any other down_revision)
    referenced = set()
    for downs in down_map.values():
        for d in downs:
            if d:
                referenced.add(d)

    heads = known - referenced
    print(f"Heads ({len(heads)}): {sorted(heads)}")


if __name__ == '__main__':
    main()
