# -*- coding: utf-8 -*-
"""PDF → image converter for architectural drawing recognition.

Usage:
    python tools/pdf_to_images.py input.pdf              # all pages → input_p1.png, input_p2.png, ...
    python tools/pdf_to_images.py input.pdf --pages 1     # page 1 only
    python tools/pdf_to_images.py input.pdf --pages 1,2   # pages 1 and 2
    python tools/pdf_to_images.py input.pdf -o output_dir  # specify output directory
    python tools/pdf_to_images.py input.pdf --dpi 300      # higher resolution
"""

import argparse
import os
import sys

import fitz  # PyMuPDF


def pdf_to_images(pdf_path, output_dir=None, pages=None, dpi=200):
    """Convert PDF pages to PNG images.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Output directory (default: same as PDF).
        pages: List of 1-based page numbers (default: all pages).
        dpi: Resolution in dots per inch (default: 200).

    Returns:
        list[str]: Paths to the generated image files.
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError("PDF not found: {}".format(pdf_path))

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(pdf_path))
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    zoom = dpi / 72.0  # PDF default is 72 dpi
    matrix = fitz.Matrix(zoom, zoom)

    doc = fitz.open(pdf_path)
    total_pages = doc.page_count

    if pages is None:
        page_indices = range(total_pages)
    else:
        page_indices = [p - 1 for p in pages if 1 <= p <= total_pages]

    output_paths = []
    for idx in page_indices:
        page = doc[idx]
        pix = page.get_pixmap(matrix=matrix)

        filename = "{}_p{}.png".format(base_name, idx + 1)
        out_path = os.path.join(output_dir, filename)
        pix.save(out_path)
        output_paths.append(out_path)

    doc.close()
    return output_paths


def main():
    parser = argparse.ArgumentParser(description="PDF to PNG converter")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("--pages", help="Page numbers (comma-separated, 1-based)")
    parser.add_argument("--dpi", type=int, default=200, help="Resolution (default: 200)")
    args = parser.parse_args()

    pages = None
    if args.pages:
        pages = [int(p.strip()) for p in args.pages.split(",")]

    paths = pdf_to_images(args.pdf, output_dir=args.output, pages=pages, dpi=args.dpi)
    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
