import pdfplumber
import re
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Node:
    level: int
    heading: str
    content: str = ""
    children: list = field(default_factory=list)
    page_num: int = 0

class PDFExtractor:

    LEVEL_PATTERNS = [
        # Level 0 — Chapter / Part / Schedule
        (0, re.compile(
            r'^(CHAPTER|PART|SCHEDULE|APPENDIX|ANNEXURE)\s+'
            r'([IVXLC\d]+|[A-Z])\b', re.IGNORECASE)),

        # Level 1 — Top-level sections e.g. "2.", "10A."
        # STRICT — only matches number+dot with wide gap or alone on line
        # Prevents "3. Eight kilometres" from matching
        (1, re.compile(
            r'^(\d{1,3}[A-Z]{0,2})\.\s*$|'        # "2." alone
            r'^(\d{1,3}[A-Z]{0,2})\.\s{3,}')),     # "2.   " wide gap

        # Level 2 — Sub-sections "(1)", "(2)"
        (2, re.compile(r'^\((\d{1,3}[A-Z]?)\)\s')),

        # Level 3 — Clauses "(a)"
        (3, re.compile(r'^\(([a-z]{1,2})\)\s')),

        # Level 4 — Sub-clauses roman numerals "(i)", "(ii)"
        (4, re.compile(
            r'^\((i{1,3}|iv|vi{0,3}|ix|x[i-v]*|'
            r'xi{1,3}|xiv|xv)\)\s', re.IGNORECASE)),

        # Level 5 — Items "A)", "B)"
        (5, re.compile(r'^([A-Z])\)\s')),

        # Level 6 — Sub-items "(I)", "(II)"
        (6, re.compile(
            r'^\((I{1,3}|IV|VI{0,3}|IX|X[I-V]*|'
            r'XI{1,3}|XIV|XV)\)\s')),
    ]

    def extract(self, pdf_path: str) -> dict:
        raw_lines = self._extract_lines_with_fonts(pdf_path)
        root = self._build_hierarchy(raw_lines)
        return self._flatten(root)

    # -------------------------------------------------------------------
    # Step 1 — Extract lines + tables per page
    # -------------------------------------------------------------------
    def _extract_lines_with_fonts(self, pdf_path: str) -> list:
        lines = []

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):

                # ── Detect table bounding boxes on this page ──────────
                table_bboxes = self._get_table_bboxes(page)

                # ── Extract tables as formatted text blocks ───────────
                table_texts = self._extract_tables_as_text(page, page_num)
                lines.extend(table_texts)

                # ── Extract words OUTSIDE table bounding boxes ────────
                words = page.extract_words(
                    extra_attrs=["size", "fontname"],
                    use_text_flow=True
                )
                if not words:
                    continue

                # Filter out words that fall inside any table bbox
                non_table_words = [
                    w for w in words
                    if not self._in_any_bbox(
                        w["x0"], w["top"], table_bboxes
                    )
                ]

                # Group remaining words into lines by y-position
                line_groups = {}
                for w in non_table_words:
                    y_key = round(w["top"], 1)
                    if y_key not in line_groups:
                        line_groups[y_key] = []
                    line_groups[y_key].append(w)

                for y_key in sorted(line_groups.keys()):
                    group = line_groups[y_key]
                    text = " ".join(w["text"] for w in group).strip()
                    if not text:
                        continue

                    avg_size = (sum(w.get("size", 10) for w in group)
                                / len(group))
                    is_bold = any(
                        "bold" in w.get("fontname", "").lower()
                        for w in group
                    )

                    lines.append({
                        "text":      text,
                        "font_size": round(avg_size, 1),
                        "is_bold":   is_bold,
                        "page":      page_num,
                        "is_table":  False   # ← not a table line
                    })

        return lines

    # -------------------------------------------------------------------
    # Table helpers
    # -------------------------------------------------------------------
    def _get_table_bboxes(self, page) -> list:
        """Return list of (x0, top, x1, bottom) for each table on page."""
        bboxes = []
        try:
            tables = page.find_tables()
            for t in tables:
                bboxes.append(t.bbox)  # (x0, top, x1, bottom)
        except Exception:
            pass
        return bboxes

    def _in_any_bbox(self, x: float, y: float, 
                     bboxes: list) -> bool:
        """Check if a word's position falls inside any table bbox."""
        for (x0, top, x1, bottom) in bboxes:
            if x0 <= x <= x1 and top <= y <= bottom:
                return True
        return False

    def _extract_tables_as_text(self, page, page_num: int) -> list:
        """
        Convert tables to readable labeled text.
        Marks them as is_table=True so heading detection skips them.

        Example table:
          A          B           C
          >10000     2km         condition X
          >100000    6km         condition Y
          >1000000   8km         condition Z

        Becomes:
          "[TABLE] Row 1: A=More than 10000 | B=Two kilometres | C=..."
        """
        table_lines = []
        try:
            tables = page.extract_tables()
            for table_idx, table in enumerate(tables):
                if not table or len(table) < 2:
                    continue

                # First row = headers (if they look like headers)
                header_row = table[0]
                headers = [
                    str(c).strip() if c else f"Col{i}"
                    for i, c in enumerate(header_row)
                ]

                # Detect if first row is actually a header
                # (short cells, no numbers)
                is_header_row = all(
                    len(str(c or "")) < 30 and
                    not re.search(r'\d{4,}', str(c or ""))
                    for c in header_row
                )

                data_rows = table[1:] if is_header_row else table

                for row_idx, row in enumerate(data_rows):
                    if not any(row):
                        continue

                    cells = [str(c).strip().replace("\n", " ")
                             if c else "" for c in row]

                    if is_header_row:
                        # "Col A=val | Col B=val | Col C=val"
                        labeled = " | ".join(
                            f"{h}={v}"
                            for h, v in zip(headers, cells)
                            if v
                        )
                        text = f"[TABLE {table_idx+1}] {labeled}"
                    else:
                        text = (f"[TABLE {table_idx+1}] "
                                f"Row {row_idx+1}: "
                                + " | ".join(c for c in cells if c))

                    if text.strip():
                        table_lines.append({
                            "text":      text,
                            "font_size": 10.0,
                            "is_bold":   False,
                            "page":      page_num,
                            "is_table":  True  # ← KEY FLAG
                        })

        except Exception as e:
            print(f"   ⚠️ Table extraction warning page {page_num}: {e}")

        return table_lines

    # -------------------------------------------------------------------
    # Step 2 — Detect font-based headers
    # -------------------------------------------------------------------
    def _get_body_font_size(self, lines: list) -> float:
        from collections import Counter
        sizes = [l["font_size"] for l in lines
                 if l["font_size"] > 0 and not l.get("is_table")]
        if not sizes:
            return 10.0
        return Counter(sizes).most_common(1)[0][0]

    def _is_font_header(self, line: dict, body_size: float) -> bool:
        # NEVER treat table lines as headers
        if line.get("is_table"):
            return False

        text = line["text"].strip()
        size = line["font_size"]

        if text.isupper() and 2 <= len(text.split()) <= 8:
            return True
        if size > body_size + 1.5:
            return True
        if line["is_bold"] and size >= body_size:
            if not self._get_legal_level(text):
                return True
        return False

    # -------------------------------------------------------------------
    # Step 3 — Legal numbering level
    # -------------------------------------------------------------------
    def _get_legal_level(self, text: str) -> Optional[tuple]:
        # NEVER match table rows
        if text.startswith("[TABLE"):
            return None
        for level, pattern in self.LEVEL_PATTERNS:
            m = pattern.match(text)
            if m:
                return (level, m.group(0).strip())
        return None

    # -------------------------------------------------------------------
    # Step 4 — Build hierarchy
    # -------------------------------------------------------------------
    def _build_hierarchy(self, lines: list) -> Node:
        body_size = self._get_body_font_size(lines)
        root  = Node(level=-1, heading="root")
        stack = [root]

        for line in lines:
            text = line["text"].strip()
            if not text:
                continue

            # Table lines → append as content to current node, never header
            if line.get("is_table"):
                if stack:
                    stack[-1].content += "\n" + text
                continue

            # Font-based header
            if self._is_font_header(line, body_size):
                node  = Node(level=0, heading=text, page_num=line["page"])
                stack = [root]
                root.children.append(node)
                stack.append(node)
                continue

            # Legal numbering
            legal = self._get_legal_level(text)
            if legal:
                level, prefix = legal
                rest = text[len(prefix):].strip()
                node = Node(
                    level=level,
                    heading=prefix,
                    content=rest,
                    page_num=line["page"]
                )
                while len(stack) > 1 and stack[-1].level >= level:
                    stack.pop()
                stack[-1].children.append(node)
                stack.append(node)
            else:
                # Plain content
                if stack:
                    stack[-1].content += " " + text

        return root

    # -------------------------------------------------------------------
    # Step 5 — Flatten to dict
    # -------------------------------------------------------------------
    def _flatten(self, root: Node,
                 parent_path: str = "",
                 result: dict = None) -> dict:
        if result is None:
            result = {}

        for child in root.children:
            path = (f"{parent_path} > {child.heading}".strip(" >")
                    if parent_path else child.heading)

            if child.content.strip():
                result[path] = child.content.strip()

            self._flatten(child, path, result)

        return result