import os
import shutil
import sys
import traceback
from pathlib import Path

import nbformat
from nbconvert import WebPDFExporter
from nbconvert.preprocessors import ExecutePreprocessor

NOTEBOOKS_DIR = Path(__file__).resolve().parent
REPO_ROOT = NOTEBOOKS_DIR.parent
PDF_DIR = NOTEBOOKS_DIR / "pdf"
WORK_DIR = Path("/tmp/jet_nb_exec")


def render_all():
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    env_pythonpath = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = f"{REPO_ROOT}:{env_pythonpath}" if env_pythonpath else str(REPO_ROOT)

    notebooks = sorted(NOTEBOOKS_DIR.glob("*.ipynb"))
    print(f"Found {len(notebooks)} notebooks in {NOTEBOOKS_DIR}")
    succeeded = []
    failed = []

    ep = ExecutePreprocessor(timeout=1800, kernel_name="python3")
    exporter = WebPDFExporter(allow_chromium_download=True)

    for nb_path in notebooks:
        print(f"\n>>> Running: {nb_path.name}")
        try:
            with open(nb_path, "r", encoding="utf-8") as f:
                nb = nbformat.read(f, as_version=4)

            ep.preprocess(nb, {"metadata": {"path": str(WORK_DIR)}})

            pdf_bytes, _ = exporter.from_notebook_node(nb)
            out_pdf = PDF_DIR / f"{nb_path.stem}.pdf"
            with open(out_pdf, "wb") as f:
                f.write(pdf_bytes)

            succeeded.append(nb_path.name)
            print(f"    [OK] -> {out_pdf.relative_to(REPO_ROOT)}")

        except Exception as exc:
            tb_str = traceback.format_exc()
            failed.append((nb_path.name, exc, tb_str))
            print(f"    [FAILED] {type(exc).__name__}: {exc}")

    shutil.rmtree(WORK_DIR, ignore_errors=True)

    lines = [
        "=" * 80,
        f"NOTEBOOK RENDERING SUMMARY ({len(succeeded)} succeeded, {len(failed)} failed)",
        "=" * 80,
        "\nSUCCEEDED:",
    ]
    for name in succeeded:
        lines.append(f"  ✓ {name}")

    lines.append("\nFAILED:")
    if not failed:
        lines.append("  (none)")
    else:
        for name, exc, tb_str in failed:
            lines.append("-" * 80)
            lines.append(f"  ✗ {name} ({type(exc).__name__})")
            lines.append(tb_str.strip())

    report = "\n".join(lines)
    print("\n" + report)

    report_path = PDF_DIR / "render_report.log"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nFull report written to: {report_path.relative_to(REPO_ROOT)}")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    render_all()
