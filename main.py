from src.extractor import PDFExtractor
from src.chunker import DocumentChunker
from src.comparator import SemanticComparator
from src.risk_analyzer import RiskAnalyzer
from src.reporter import Reporter
import argparse
import json
import os
import sys

def compare_documents(pdf_v1: str, pdf_v2: str, output_format: str = "html"):
    os.makedirs("output", exist_ok=True)

    print("📄 Extracting PDFs...")
    extractor = PDFExtractor()
    sections_v1 = extractor.extract(pdf_v1)
    sections_v2 = extractor.extract(pdf_v2)

    print("✂️  Chunking...")
    chunker = DocumentChunker()
    chunks_v1 = chunker.chunk_sections(sections_v1)
    chunks_v2 = chunker.chunk_sections(sections_v2)
    print(f"   v1: {len(chunks_v1)} chunks | v2: {len(chunks_v2)} chunks")

    print("🔍 Comparing semantically...")
    comparator = SemanticComparator()
    diff = comparator.compare(chunks_v1, chunks_v2)

    print("⚠️  Assessing risks...")
    analyzer = RiskAnalyzer()
    # After diff is computed, before risk analysis
    total_changes = (len(diff["additions"]) + 
                 len(diff["deletions"]) + 
                 len(diff["updates"]))

    print(f"\n   Total changes found: {total_changes}")

    if total_changes > 1000:
        print(f"   ⚠️  Large diff detected — "
          f"rule-based analysis will handle bulk, "
          f"LLM reserved for top critical changes only")
    risks = analyzer.analyze(diff)

    report = {
        "summary": {
            "additions":     len(diff["additions"]),
            "deletions":     len(diff["deletions"]),
            "updates":       len(diff["updates"]),
            "total_risks":   len(risks),
            "critical_risks": sum(1 for r in risks if r["risk_level"] == "critical"),
            "high_risks":    sum(1 for r in risks if r["risk_level"] == "high"),
        },
        "changes": diff,
        "risks": risks
    }

    with open("output/report.json", "w") as f:
        json.dump(report, f, indent=2)

    ext = "md" if output_format == "md" else "html"
    output_path = f"output/report.{ext}"

    reporter = Reporter()
    reporter.generate(
        report,
        output_path=output_path,
        doc1_name=os.path.basename(pdf_v1),
        doc2_name=os.path.basename(pdf_v2),
        fmt=output_format,
    )

    _print_summary(report["summary"], risks[:5])

def _print_summary(summary, top_risks):
    print("\n" + "="*50)
    print("📊 SUMMARY")
    print("="*50)
    print(f"  ➕ Additions : {summary['additions']}")
    print(f"  ✏️  Updates   : {summary['updates']}")
    print(f"  ❌ Deletions : {summary['deletions']}")
    print(f"  🔴 Critical  : {summary['critical_risks']}")
    print(f"  🟠 High      : {summary['high_risks']}")
    if top_risks:
        print("\n📌 Top Risks:")
        for r in top_risks:
            print(f"  [{r['risk_level'].upper()}] {r['section']} — {r['risk_reason']}")

def main():
    parser = argparse.ArgumentParser(
        description="Compare two policy PDFs and generate a diff report."
    )
    parser.add_argument("pdf_v1", help="Path to the first PDF")
    parser.add_argument("pdf_v2", help="Path to the second PDF")
    parser.add_argument(
        "--format", "-f",
        choices=["html", "md"],
        default="html",
        help="Report output format (default: html)",
    )
    args = parser.parse_args()
    compare_documents(args.pdf_v1, args.pdf_v2, output_format=args.format)

if __name__ == "__main__":
    main()
