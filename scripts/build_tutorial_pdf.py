from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "working" / "guide" / "DoW2 Tools Tutorial.md"
DEFAULT_OUTPUT = REPO_ROOT / "working" / "guide" / "DoW2 Tools Tutorial.pdf"
SIMULATOR_INPUT = REPO_ROOT / "working" / "guide" / "Havok Simulator Guide.md"
SIMULATOR_OUTPUT = REPO_ROOT / "working" / "guide" / "Havok Simulator Guide.pdf"

GUIDE_TARGETS = {
    "addon": (DEFAULT_INPUT, DEFAULT_OUTPUT),
    "simulator": (SIMULATOR_INPUT, SIMULATOR_OUTPUT),
}


def _find_browser() -> str:
    candidates = [
        "msedge",
        "chrome",
        "chromium",
        "google-chrome",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for candidate in candidates:
        resolved = shutil.which(candidate) if os.path.basename(candidate) == candidate else candidate
        if resolved and os.path.exists(resolved):
            return resolved
    return ""


def _inline_markup(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    return escaped


def _markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    output: list[str] = []
    in_list = False
    in_code = False
    code_lines: list[str] = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            output.append("</ul>")
            in_list = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                close_list()
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        image_match = re.match(r"!\[(.*?)\]\((.*?)\)", stripped)
        if image_match:
            close_list()
            alt_text = html.escape(image_match.group(1))
            src = html.escape(image_match.group(2))
            output.append(f'<figure><img src="{src}" alt="{alt_text}"></figure>')
            continue

        if stripped.startswith("#"):
            close_list()
            marker, _, title = stripped.partition(" ")
            level = min(len(marker), 6)
            output.append(f"<h{level}>{_inline_markup(title)}</h{level}>")
            continue

        if stripped.startswith("- "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{_inline_markup(stripped[2:])}</li>")
            continue

        if not stripped:
            close_list()
            continue

        close_list()
        output.append(f"<p>{_inline_markup(stripped)}</p>")

    close_list()
    return "\n".join(output)


def _render_html_document(markdown_path: Path) -> str:
    body = _markdown_to_html(markdown_path.read_text(encoding="utf-8"))
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{html.escape(markdown_path.stem)}</title>
  <style>
    @page {{ margin: 0.65in; }}
    body {{ font-family: Arial, Helvetica, sans-serif; font-size: 11pt; line-height: 1.45; color: #1f1f1f; }}
    h1 {{ font-size: 24pt; margin: 0 0 18px; }}
    h2 {{ font-size: 18pt; margin: 28px 0 10px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }}
    h3 {{ font-size: 14pt; margin: 20px 0 8px; }}
    p {{ margin: 0 0 10px; }}
    ul {{ margin: 0 0 12px 22px; padding: 0; }}
    li {{ margin: 0 0 5px; }}
    code {{ font-family: Consolas, 'Courier New', monospace; background: #f2f2f2; padding: 1px 4px; border-radius: 3px; }}
    pre {{ background: #f4f4f4; padding: 10px; border-radius: 4px; overflow-wrap: anywhere; white-space: pre-wrap; }}
    figure {{ margin: 14px 0 6px; break-inside: avoid; }}
    img {{ max-width: 100%; border: 1px solid #c8c8c8; }}
    em {{ color: #555; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def _run_pandoc(markdown_path: Path, pdf_path: Path) -> bool:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        return False
    command = [
        pandoc,
        str(markdown_path),
        "--resource-path",
        str(markdown_path.parent),
        "-o",
        str(pdf_path),
    ]
    subprocess.run(command, check=True)
    return True


def _run_browser(markdown_path: Path, pdf_path: Path) -> None:
    browser = _find_browser()
    if not browser:
        raise RuntimeError("No supported browser found. Install Microsoft Edge, Chrome, Chromium, or pandoc.")

    html_path = markdown_path.with_suffix(".pdf-build.html")
    html_path.write_text(_render_html_document(markdown_path), encoding="utf-8")
    try:
        command = [
            browser,
            "--headless",
            "--disable-gpu",
            "--allow-file-access-from-files",
            "--no-pdf-header-footer",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={pdf_path}",
            str(html_path),
        ]
        subprocess.run(command, check=True)
    finally:
        try:
            html_path.unlink()
        except OSError:
            pass


def build_pdf(markdown_path: Path, pdf_path: Path) -> None:
    markdown_path = markdown_path.resolve()
    pdf_path = pdf_path.resolve()
    if not markdown_path.is_file():
        raise FileNotFoundError(markdown_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if not _run_pandoc(markdown_path, pdf_path):
        _run_browser(markdown_path, pdf_path)


def build_named_guide(name: str, output_override: Path | None = None) -> Path:
    markdown_path, default_pdf_path = GUIDE_TARGETS[name]
    pdf_path = output_override if output_override is not None else default_pdf_path
    build_pdf(markdown_path, pdf_path)
    return pdf_path.resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the DoW2 Tools tutorial PDF from Markdown.")
    parser.add_argument("input", nargs="?", help="Markdown tutorial path")
    parser.add_argument("-o", "--output", help="Output PDF path")
    parser.add_argument(
        "--guide",
        choices=sorted(GUIDE_TARGETS.keys()),
        help="Build one of the named guide PDFs using its default paths.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Build all named guide PDFs.",
    )
    args = parser.parse_args(argv)

    try:
        if args.input:
            if args.all or args.guide:
                raise ValueError("Do not combine an explicit input path with --guide or --all.")

            output_path = Path(args.output) if args.output else Path(args.input).with_suffix(".pdf")
            build_pdf(Path(args.input), output_path)
            print(f"Wrote {output_path.resolve()}")
            return 0

        if args.all:
            if args.output:
                raise ValueError("--output cannot be used with --all.")

            built_paths = [build_named_guide(name) for name in ("addon", "simulator")]
            for built_path in built_paths:
                print(f"Wrote {built_path}")
            return 0

        guide_name = args.guide or "addon"
        built_path = build_named_guide(guide_name, Path(args.output) if args.output else None)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {built_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())