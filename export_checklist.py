"""Export training checklist Excel from trainning_be.txt.

Reads the structured training plan text file and builds an Excel checklist
in a simple tabular layout similar to Checklist Training BE.xlsx.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def parse_plan(txt_path: Path):
    """Parse trainning_be.txt into task dictionaries."""

    raw = txt_path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    stage_re = re.compile(r"^##\s+GIAI ĐOẠN\s+\d+:\s*(.*)", re.IGNORECASE)
    date_re = re.compile(r"^###\s+([^#]+)")
    task_re = re.compile(r"^\*\*Task\s*(\d+)\s*:\*\*\s*(.*)")
    status_re = re.compile(r"^\*\*Status:\*\*\s*(.*)", re.IGNORECASE)

    items = []
    current_stage = None
    current_date = None
    current_task = None
    details = []

    def flush_current():
        nonlocal current_task, details
        if current_task is None:
            return
        current_task["details"] = " ".join(details).strip()
        items.append(current_task)
        current_task = None
        details = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        stage_match = stage_re.match(stripped)
        if stage_match:
            flush_current()
            current_stage = stage_match.group(1).strip()
            continue

        date_match = date_re.match(stripped)
        if date_match:
            flush_current()
            current_date = date_match.group(1).strip()
            continue

        task_match = task_re.match(stripped)
        if task_match:
            flush_current()
            current_task = {
                "stage": current_stage,
                "date": current_date,
                "task_no": task_match.group(1).strip(),
                "title": task_match.group(2).strip(),
                "status": None,
            }
            details = []
            continue

        status_match = status_re.match(stripped)
        if status_match and current_task is not None:
            status_text = status_match.group(1).lower()
            status_value = "true" in status_text or "✅" in status_text
            current_task["status"] = status_value
            flush_current()
            continue

        if current_task is not None:
            cleaned = stripped.strip("-* ")
            cleaned = cleaned.replace("**", "")
            if cleaned:
                details.append(cleaned)

    flush_current()
    return items


def build_excel(items, output_path: Path):
    """Create Excel workbook from parsed items."""

    wb = Workbook()
    ws = wb.active
    ws.title = "Checklist"

    ws.append(["Checklist BE - Generated", None, None, None, None, None])
    ws.append([])
    ws.append(["Stage", "Date", "Task #", "Task", "Details", "Status"])

    for item in items:
        ws.append(
            [
                item.get("stage"),
                item.get("date"),
                item.get("task_no"),
                item.get("title"),
                item.get("details"),
                item.get("status"),
            ]
        )

    header_font = Font(bold=True)
    for cell in ws[3]:
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    widths = {
        "A": 32,
        "B": 18,
        "C": 8,
        "D": 38,
        "E": 90,
        "F": 10,
    }
    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    ws.freeze_panes = "A4"
    wb.save(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Export training checklist Excel from trainning_be.txt",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("trainning_be.txt"),
        help="Path to training plan text file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("checklist_from_txt.xlsx"),
        help="Output Excel file path",
    )
    args = parser.parse_args()

    items = parse_plan(args.input)
    if not items:
        raise SystemExit("No tasks parsed; check input format.")

    build_excel(items, args.output)
    print(f"Wrote {len(items)} tasks to {args.output}")


if __name__ == "__main__":
    main()
