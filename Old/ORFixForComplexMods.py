import os
import re
import shutil
from datetime import datetime
import sys

# Detect color support
SUPPORTS_COLOR = sys.stdout.isatty()
RED = "\033[91m" if SUPPORTS_COLOR else ""
GREEN = "\033[92m" if SUPPORTS_COLOR else ""
RESET = "\033[0m" if SUPPORTS_COLOR else ""

# Auto-exclusion patterns
AUTO_EXCLUDE_PATTERNS = [
    re.compile(r'^\[(CommandList|TextureOverride).*IB\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*Position\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*Texcoord\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*Blend\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*Info\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*VertexLimitRaise\]$', re.IGNORECASE),
]

# Patterns
SWAPVAR_PATTERN = re.compile(r'^\s*(if|else if)\s+\$swapvar\s*==\s*(\d+)', re.IGNORECASE)
RUN_LINE_PATTERN = re.compile(r'\s*run\s*=\s*CommandList\\global\\ORFix\\(NNFix|ORFix)', re.IGNORECASE)
RESOURCE_END_PATTERN = re.compile(r'^\s*\[Resource.*Position.*\]', re.IGNORECASE)

rename_extra_ps = None  # global toggle


def process_block_full(block, section_name, is_excluded=False):
    """
    Process a block:
    - Skip completely if is_excluded=True
    - Otherwise: rename ps-t0->ps-t1, remove misplaced runs, add correct run line
    """
    if not block or is_excluded:
        return block, []

    changes = []
    has_normal = any("NormalMap" in line for line in block)
    correct_run = "run = CommandList\\global\\ORFix\\ORFix\n" if has_normal else "run = CommandList\\global\\ORFix\\NNFix\n"

    new_block = []
    last_ps_indices = {}

    for i, line in enumerate(block):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Rename ps-t0 -> ps-t1 if Extra+Diffuse and user agreed
        if rename_extra_ps and re.match(r'ps-t0\s*=', stripped) and "Extra" in stripped and "Diffuse" in stripped:
            new_block.append(line.replace("ps-t0", "ps-t1", 1))
            changes.append(f"{section_name} → RENAMED: {stripped} -> {stripped.replace('ps-t0','ps-t1',1)}")
        else:
            new_block.append(line)

        # Track last ps-t per indentation for run insertion
        if re.match(r'ps-t\d+', stripped):
            last_ps_indices[indent] = len(new_block) - 1

    # Remove misplaced run lines
    temp_block = []
    for i, line in enumerate(new_block):
        if RUN_LINE_PATTERN.match(line):
            indent = len(line) - len(line.lstrip())
            if indent in last_ps_indices and i == last_ps_indices[indent] + 1 and line == correct_run:
                temp_block.append(line)
            else:
                changes.append(f"{section_name} → REMOVED misplaced run: {line.strip()}")
        else:
            temp_block.append(line)
    new_block = temp_block

    # Insert run lines after last ps-t per indentation if missing
    for indent, last_index in sorted(last_ps_indices.items()):
        insert_index = last_index + 1
        if not (len(new_block) > insert_index and new_block[insert_index] == correct_run):
            new_block.insert(insert_index, correct_run)
            changes.append(f"{section_name} → ADDED run line: {correct_run.strip()}")
            # Adjust indices for subsequent insertions
            for k in last_ps_indices:
                if last_ps_indices[k] >= insert_index:
                    last_ps_indices[k] += 1

    return new_block, changes


def process_ini_preview(file_path, exclude_sections):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    block_lines = []
    current_section = None
    inside_section = False
    inside_excluded = False
    current_swapvar = None
    all_changes = []

    for line in lines:
        stripped = line.strip()

        # Detect section headers
        if stripped.startswith("[CommandList") or stripped.startswith("[TextureOverride"):
            if block_lines:
                processed, changes = process_block_full(block_lines, current_section, is_excluded=inside_excluded)
                new_lines.extend(processed)
                all_changes.extend(changes)
                block_lines.clear()

            current_section = stripped
            inside_section = True
            inside_excluded = any(pat.match(current_section) for pat in AUTO_EXCLUDE_PATTERNS) or current_section in exclude_sections
            current_swapvar = None
            new_lines.append(line)
            continue

        # Swapvar detection
        swapvar_match = SWAPVAR_PATTERN.match(line)
        if swapvar_match:
            if block_lines:
                processed, changes = process_block_full(block_lines, current_section, is_excluded=inside_excluded)
                new_lines.extend(processed)
                all_changes.extend(changes)
                block_lines.clear()
            current_swapvar = swapvar_match.group(2)
            block_lines.append(line)
        elif inside_section and re.match(r'\s*endif', line, re.IGNORECASE):
            block_lines.append(line)
            processed, changes = process_block_full(block_lines, current_section, is_excluded=inside_excluded)
            new_lines.extend(processed)
            all_changes.extend(changes)
            block_lines.clear()
            current_swapvar = None
        elif inside_section:
            block_lines.append(line)
        else:
            new_lines.append(line)

    if block_lines:
        processed, changes = process_block_full(block_lines, current_section, is_excluded=inside_excluded)
        new_lines.extend(processed)
        all_changes.extend(changes)

    return all_changes, new_lines


def main():
    global rename_extra_ps

    # Ask about renaming ps-t0 -> ps-t1 for Extra+Diffuse
    while True:
        choice = input(
            'Rename ps-t0 lines containing "Extra" and "Diffuse" to ps-t1 in [TextureOverride...] or [CommandList...]? (y/n): '
        ).strip().lower()
        if choice in ('y','n'):
            rename_extra_ps = choice == 'y'
            break

    recursive = input("Scan subfolders too? (y/n): ").strip().lower() == 'y'

    ini_files = []
    sections_found = set()

    for root, dirs, files in os.walk('.', topdown=True):
        if not recursive and root != '.':
            continue
        for file in files:
            if file.lower().endswith('.ini'):
                path = os.path.join(root, file)
                ini_files.append(path)
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("[CommandList") or line.startswith("[TextureOverride"):
                            sections_found.add(line)
        if not recursive:
            break

    # Auto + interactive exclusion
    exclude_sections = set()
    for section in sorted(sections_found):
        if any(pat.match(section) for pat in AUTO_EXCLUDE_PATTERNS):
            exclude_sections.add(section)
            print(f"Auto-excluded {section}")
            continue
        while True:
            choice = input(f"Exclude {section}? (y/n): ").strip().lower()
            if choice in ("y","n"):
                break
        if choice == "y":
            exclude_sections.add(section)

    # Preview changes
    all_changes = {}
    for fpath in ini_files:
        changes, _ = process_ini_preview(fpath, exclude_sections)
        if changes:
            all_changes[fpath] = changes

    if not all_changes:
        print("\nNo changes detected.")
    else:
        print("\n=== Proposed Changes ===")
        for f, changes in all_changes.items():
            print(f"\nFile: {f}")
            for c in changes:
                if "ADDED" in c:
                    print(f"  {GREEN}{c}{RESET}")
                elif "REMOVED" in c or "RENAMED" in c:
                    print(f"  {RED}{c}{RESET}")
                else:
                    print(f"  {c}")
        print("=========================")

        proceed = input("\nProceed with these changes? (y/n): ").strip().lower()
        if proceed == 'y':
            for fpath in all_changes.keys():
                _, new_lines = process_ini_preview(fpath, exclude_sections)
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                backup_path = f"{fpath}.bak_{timestamp}"
                shutil.copyfile(fpath, backup_path)
                with open(fpath, 'w', encoding='utf-8') as out:
                    out.writelines(new_lines)
                print(f"\n✅ Updated: {fpath}\n  Backup: {backup_path}")
            print("\nAll changes applied successfully.")
        else:
            print("Aborted — no changes made.")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
