"""
json_to_txt.py
--------------
Converts report JSON files (like report_180835.json) to structured .txt files.

Usage:
    # Single file
    python json_to_txt.py report_180835.json

    # Multiple files
    python json_to_txt.py report_1.json report_2.json

    # All JSON files in a directory
    python json_to_txt.py --dir ./reports

    # Specify output directory
    python json_to_txt.py --dir ./reports --out ./output_txts
"""

import json
import argparse
from pathlib import Path


# ── Field labels ─────────────────────────────────────────────────────────────
# Customize these to rename or reorder how fields appear in the .txt output.

SECTION_LABELS = {
    "basic_info":       "Basic Information",
    "lifestyle":        "Lifestyle",
    "medical_history":  "Medical History",
    "symptoms":         "Symptoms",
    "history":          "Session History",
}

FIELD_LABELS = {
    # basic_info
    "gender":            "Gender",
    "age":               "Age",
    "weight":            "Weight (kg)",
    "height":            "Height (cm)",
    # lifestyle
    "smoking":           "Smoking Status",
    "physical_activity": "Physical Activity",
    # medical_history
    "chronic":           "Chronic Conditions",
    "meds":              "Current Medications",
    "family":            "Family History",
    # symptoms
    "desc":              "Symptom Description",
    # history
    "history":           "History",
}


def flatten_value(value) -> str:
    """Convert any JSON value to a readable string."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "—"
    if value is None or value == "":
        return "—"
    return str(value)


def json_to_txt(data: dict) -> str:
    """Build the full text content from a parsed JSON report."""
    lines = []

    for section_key, section_value in data.items():
        # Section header
        section_label = SECTION_LABELS.get(section_key, section_key.replace("_", " ").title())
        lines.append(f"{'=' * 40}")
        lines.append(f"  {section_label}")
        lines.append(f"{'=' * 40}")

        if isinstance(section_value, dict):
            for field_key, field_value in section_value.items():
                label = FIELD_LABELS.get(field_key, field_key.replace("_", " ").title())
                lines.append(f"  {label:<25} {flatten_value(field_value)}")
        elif isinstance(section_value, list):
            label = FIELD_LABELS.get(section_key, section_key.replace("_", " ").title())
            lines.append(f"  {label:<25} {flatten_value(section_value)}")
        else:
            lines.append(f"  {flatten_value(section_value)}")

        lines.append("")  # blank line between sections

    return "\n".join(lines)


def process_file(json_path: Path, out_dir: Path) -> Path:
    """Read one JSON file, convert it, and write the .txt output."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    txt_content = json_to_txt(data)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (json_path.stem + ".txt")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(txt_content)

    print(f"  ✓  {json_path.name}  →  {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Convert report JSON files to .txt")
    parser.add_argument("files", nargs="*", help="JSON file(s) to convert")
    parser.add_argument("--dir", help="Directory containing JSON files to batch-convert")
    parser.add_argument("--out", default=".", help="Output directory (default: same as input)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    json_files = []

    if args.dir:
        json_files = list(Path(args.dir).glob("*.json"))
        if not json_files:
            print(f"No .json files found in: {args.dir}")
            return

    if args.files:
        json_files += [Path(f) for f in args.files]

    if not json_files:
        parser.print_help()
        return

    print(f"\nConverting {len(json_files)} file(s)...\n")
    for jf in json_files:
        # If no explicit --out, put the txt next to the source json
        target_dir = out_dir if args.out != "." else jf.parent
        process_file(jf, target_dir)

    print("\nDone.")


if __name__ == "__main__":
    main()