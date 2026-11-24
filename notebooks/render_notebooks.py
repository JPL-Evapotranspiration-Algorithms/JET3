import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

import nbformat
from nbconvert import PDFExporter, WebPDFExporter
from nbconvert.preprocessors import ExecutePreprocessor

NOTEBOOKS_DIR = Path(__file__).resolve().parent
REPO_ROOT = NOTEBOOKS_DIR.parent
PDF_DIR = NOTEBOOKS_DIR / "pdf"
WORK_DIR = Path("/tmp/jet_nb_exec")


def _has_local_chromium() -> bool:
    """Check if Playwright has a cached Chromium binary available locally."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            exe = Path(p.chromium.executable_path)
            return exe.is_file()
    except Exception:
        return False


def _has_local_latex() -> bool:
    """Check if pandoc and a LaTeX engine (xelatex/pdflatex) are installed locally."""
    has_pandoc = shutil.which("pandoc") is not None
    has_tex = any(shutil.which(cmd) is not None for cmd in ("xelatex", "pdflatex", "lualatex"))
    return has_pandoc and has_tex


def get_local_exporter():
    """Select an offline-capable PDF exporter, preferring local WebPDF with LaTeX fallback."""
    if _has_local_chromium():
        print("Using local WebPDFExporter (cached Chromium found).")
        return WebPDFExporter(allow_chromium_download=False)

    if _has_local_latex():
        print("Local Chromium not found; falling back to local LaTeX PDFExporter.")
        return PDFExporter()

    raise RuntimeError(
        "No local PDF rendering backend found. Install Chromium offline via "
        "'playwright install chromium' or install pandoc + TeX Live/MacTeX."
    )


def render_all():
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    env_pythonpath = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = f"{REPO_ROOT}:{env_pythonpath}" if env_pythonpath else str(REPO_ROOT)

    # Disable automatic downloads in nbconvert/playwright
    os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"

    exporter = get_local_exporter()
    ep = ExecutePreprocessor(timeout=1800, kernel_name="python3")

    notebooks = sorted(NOTEBOOKS_DIR.glob("*.ipynb"))
    print(f"Found {len(notebooks)} notebooks in {NOTEBOOKS_DIR}")
    succeeded = []
    failed = []

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