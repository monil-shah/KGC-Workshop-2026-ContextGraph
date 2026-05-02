"""Compare how different chunking strategies split the same document."""
import os
import re
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# Load a sample document
data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "01-knowledge-base-setup", "data")
with open(os.path.join(data_dir, "metric-definitions.md")) as f:
    document = f.read()

console.print(Panel(f"Document: metric-definitions.md ({len(document)} chars)", style="bold blue"))


def fixed_size_chunk(text: str, max_chars: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into fixed-size chunks with overlap."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def semantic_chunk(text: str) -> list[str]:
    """Split on paragraph boundaries (simulates semantic chunking)."""
    paragraphs = re.split(r"\n\n+", text)
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) > 1500:
            if current:
                chunks.append(current.strip())
            current = para
        else:
            current += "\n\n" + para
    if current.strip():
        chunks.append(current.strip())
    return chunks


def hierarchical_chunk(text: str) -> dict:
    """Split into parent (sections) and child (paragraphs) chunks."""
    sections = re.split(r"\n(?=## )", text)
    result = {}
    for section in sections:
        if not section.strip():
            continue
        lines = section.strip().split("\n")
        title = lines[0].strip("# ").strip()
        children = re.split(r"\n\n+", section)
        children = [c.strip() for c in children if c.strip() and len(c.strip()) > 20]
        result[title] = {"parent": section.strip(), "children": children}
    return result


def markdown_header_chunk(text: str) -> list[dict]:
    """Custom: split on markdown headers with metadata."""
    sections = re.split(r"\n(?=##+ )", text)
    chunks = []
    for section in sections:
        if not section.strip():
            continue
        lines = section.strip().split("\n")
        header_match = re.match(r"^(#+)\s+(.+)", lines[0])
        title = header_match.group(2) if header_match else "Introduction"
        level = len(header_match.group(1)) if header_match else 1
        chunks.append({
            "text": section.strip(),
            "metadata": {
                "section_title": title,
                "header_level": level,
                "char_count": len(section),
                "has_table": "|" in section and "---" in section,
                "has_code": "```" in section,
            },
        })
    return chunks


# Run all strategies
console.print("\n[bold green]1. Fixed-Size Chunking[/] (1000 chars, 200 overlap)")
fixed = fixed_size_chunk(document)
for i, chunk in enumerate(fixed):
    console.print(f"  Chunk {i+1}: {len(chunk)} chars — {chunk[:80].replace(chr(10), ' ')}...")

console.print(f"\n[bold green]2. Semantic Chunking[/] (paragraph boundaries)")
semantic = semantic_chunk(document)
for i, chunk in enumerate(semantic):
    console.print(f"  Chunk {i+1}: {len(chunk)} chars — {chunk[:80].replace(chr(10), ' ')}...")

console.print(f"\n[bold green]3. Hierarchical Chunking[/] (sections → paragraphs)")
hierarchical = hierarchical_chunk(document)
for title, data in hierarchical.items():
    console.print(f"  Parent: {title} ({len(data['parent'])} chars, {len(data['children'])} children)")

console.print(f"\n[bold green]4. Custom Markdown Header Chunking[/] (with metadata)")
custom = markdown_header_chunk(document)
for chunk in custom:
    meta = chunk["metadata"]
    console.print(
        f"  {'  ' * (meta['header_level']-1)}[{'H' + str(meta['header_level'])}] "
        f"{meta['section_title']} — {meta['char_count']} chars"
        f"{' 📊' if meta['has_table'] else ''}{' 💻' if meta['has_code'] else ''}"
    )

# Summary
table = Table(title="\nChunking Strategy Comparison")
table.add_column("Strategy", style="cyan")
table.add_column("Chunks", justify="right")
table.add_column("Avg Size", justify="right")
table.add_column("Preserves Structure", justify="center")
table.add_column("Metadata", justify="center")

table.add_row("Fixed-Size", str(len(fixed)), f"{sum(len(c) for c in fixed)//len(fixed)} chars", "❌", "❌")
table.add_row("Semantic", str(len(semantic)), f"{sum(len(c) for c in semantic)//len(semantic)} chars", "✅", "❌")
table.add_row("Hierarchical", str(len(hierarchical)), "varies", "✅", "❌")
table.add_row("Custom Lambda", str(len(custom)), f"{sum(c['metadata']['char_count'] for c in custom)//len(custom)} chars", "✅", "✅")

console.print(table)
