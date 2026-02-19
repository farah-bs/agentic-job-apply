import time
import requests
from pathlib import Path


LATEX_ONLINE_URL = "https://latexonline.cc/compile"


def compile_latex_to_pdf(tex_path: str, output_pdf_path: str = None, timeout: int = 60) -> str:
    """
    Upload a .tex file to LaTeX.Online and download the compiled PDF.

    Args:
        tex_path:        Path to the .tex file
        output_pdf_path: Where to save the PDF (defaults to same name as .tex)
        timeout:         Request timeout in seconds

    Returns:
        Path to the saved PDF file

    Raises:
        RuntimeError: If compilation fails
    """
    tex_path = Path(tex_path)
    if not tex_path.exists():
        raise FileNotFoundError(f"LaTeX file not found: {tex_path}")

    if output_pdf_path is None:
        output_pdf_path = tex_path.with_suffix(".pdf")
    output_pdf_path = Path(output_pdf_path)

    print(f"Sending {tex_path.name} to LaTeX.Online...")

    with open(tex_path, "rb") as f:
        response = requests.post(
            LATEX_ONLINE_URL,
            files={"file": (tex_path.name, f, "application/x-tex")},
            timeout=timeout,
        )

    if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("application/pdf"):
        output_pdf_path.write_bytes(response.content)
        size_kb = len(response.content) // 1024
        print(f"PDF compiled successfully ({size_kb} KB) → {output_pdf_path}")
        return str(output_pdf_path)

    # Try to extract error message from response
    error_text = response.text[:500] if response.text else f"HTTP {response.status_code}"
    raise RuntimeError(f"LaTeX compilation failed:\n{error_text}")


def compile_with_retry(tex_path: str, output_pdf_path: str = None, retries: int = 2) -> str:
    """Wrapper with retry logic for transient network failures."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return compile_latex_to_pdf(tex_path, output_pdf_path)
        except RuntimeError as e:
            last_error = e
            if attempt < retries:
                print(f"Attempt {attempt} failed, retrying in 3s...")
                time.sleep(3)
    raise RuntimeError(f"Compilation failed after {retries} attempts: {last_error}")
