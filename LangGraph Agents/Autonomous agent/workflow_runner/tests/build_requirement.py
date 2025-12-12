#!/usr/bin/env python3
import re
from pathlib import Path
from collections import OrderedDict


def load_reqs(path: str) -> OrderedDict:
    """
    Parse a pip requirements file into an OrderedDict of {package: line}.
    Comments and blank lines are kept under their exact text.
    """
    reqs = OrderedDict()
    pkg_line = re.compile(r"^\s*([A-Za-z0-9_.\-]+)([<=>!~].*)?$")

    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            # preserve comments or blanks
            reqs[raw] = None
            continue

        m = pkg_line.match(line)
        if m:
            pkg = m.group(1).lower()
            reqs[pkg] = raw
        else:
            # unknown format, preserve verbatim
            reqs[raw] = None
    return reqs


def merge(original_path: str, new_path: str, output_path: str) -> None:
    """
    Merge two requirements files:
      - Keep all entries from original_path in order
      - Append entries from new_path whose package names are not in original
      - Preserve comments and blank lines
    """
    orig = load_reqs(original_path)
    new  = load_reqs(new_path)

    merged = OrderedDict()
    # 1) take original entries
    for key, line in orig.items():
        merged[key] = line

    # 2) append unique new entries
    for key, line in new.items():
        if key not in merged:
            merged[key] = line

    # 3) write merged file
    with open(output_path, "w") as f:
        for key, line in merged.items():
            if line is None:
                f.write(f"{key}\n")
            else:
                f.write(f"{line}\n")
    print(f"Merged requirements written to {output_path}")


def main():
    # Direct paths to your files; adjust as needed
    original = r"D:\Office Work\workflow_branches\ai-workflow-research-py\project\app\requirements.txt"
    new_file = r"D:\Office Work\workflow_branches\requirements.txt"
    output = r"D:\Office Work\workflow_branches\ai-workflow-research-py\project\app\WorkflowRunner\requirements-merged.txt"
    merge(original, new_file, output)


if __name__ == "__main__":
    main()
