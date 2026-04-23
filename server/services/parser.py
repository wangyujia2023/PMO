import re
from typing import List

from server.models import ReportBlock


PROJECT_HEADER_RE = re.compile(r"^\s*(\d+)[\.\、]\s*(.+?)\s*$")
NEXT_PLAN_RE = re.compile(r"^\s*下周(?:工作|计划)?[:：]?\s*$")
ENUM_LINE_RE = re.compile(r"^\s*\d+[\.\、]\s*")


def split_blocks(raw_text: str) -> List[ReportBlock]:
    lines = [line.rstrip() for line in raw_text.splitlines()]
    blocks: List[tuple[int, str, List[str]]] = []
    current_name = ""
    current_lines: List[str] = []
    current_index = 0

    for line in lines:
        matched = PROJECT_HEADER_RE.match(line)
        if matched:
            if current_name:
                blocks.append((current_index, current_name, current_lines))
            current_index = int(matched.group(1))
            current_name = matched.group(2).strip()
            current_lines = []
            continue
        if current_name:
            current_lines.append(line)

    if current_name:
        blocks.append((current_index, current_name, current_lines))

    return [build_report_block(index, project_name, block_lines) for index, project_name, block_lines in blocks]


def build_report_block(index: int, project_name: str, lines: List[str]) -> ReportBlock:
    current_part: List[str] = []
    next_part: List[str] = []
    in_next = False

    for line in lines:
        if NEXT_PLAN_RE.match(line):
            in_next = True
            continue
        cleaned = ENUM_LINE_RE.sub("", line).strip()
        if not cleaned:
            continue
        if in_next:
            next_part.append(cleaned)
        else:
            current_part.append(cleaned)

    raw_text = "\n".join([project_name] + [line for line in lines if line.strip()])
    return ReportBlock(
        index=index,
        project_name=project_name,
        current_progress="\n".join(current_part),
        next_plan="\n".join(next_part),
        raw_text=raw_text,
    )
