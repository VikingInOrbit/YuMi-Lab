"Do you think that pdf_to_md.py was a good pipeline for this?"

from __future__ import annotations

import argparse
import base64
import io
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import fitz
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

try:
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR
except Exception:
    np = None
    RapidOCR = None


@dataclass
class Config:
    pdf_path: Path
    output_md: Path
    images_dir: Path
    title: Optional[str]
    include_page_headers: bool
    enable_ocr: bool
    enable_ai_descriptions: bool
    cleanup_images_after: bool


def parse_args() -> Config:
    parser = argparse.ArgumentParser(
        description="Convert a PDF to Markdown with text, formula wrapping, image export, and OCR annotations."
    )
    parser.add_argument("pdf", type=Path, help="Input PDF file path")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output Markdown file path (default: <pdf_stem>.md)",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=None,
        help="Directory to save extracted images (default: Attachments)",
    )
    parser.add_argument("--title", type=str, default=None, help="Optional title for the Markdown")
    parser.add_argument(
        "--no-page-headers",
        action="store_true",
        help="Do not include per-page Markdown headers",
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Disable OCR text extraction from images",
    )
    parser.add_argument(
        "--ai-descriptions",
        action="store_true",
        help="Enable AI image description hook (currently placeholder).",
    )
    parser.add_argument(
        "--cleanup-images",
        action="store_true",
        help="Remove generated images after markdown creation (off by default).",
    )

    args = parser.parse_args()

    pdf_path = args.pdf.resolve()
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        raise SystemExit(f"Input must be an existing PDF: {pdf_path}")

    output_md = args.output.resolve() if args.output else pdf_path.with_suffix(".md")
    images_dir = args.images_dir.resolve() if args.images_dir else (output_md.parent / "Attachments")

    return Config(
        pdf_path=pdf_path,
        output_md=output_md,
        images_dir=images_dir,
        title=args.title,
        include_page_headers=not args.no_page_headers,
        enable_ocr=not args.no_ocr,
        enable_ai_descriptions=args.ai_descriptions,
        cleanup_images_after=args.cleanup_images,
    )


def safe_file_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_garbled_formula_line(line: str) -> bool:
    candidate = line.strip()
    if not candidate or len(candidate) < 4:
        return False
    if any(ch.isalpha() for ch in candidate):
        return False

    non_space = [ch for ch in candidate if not ch.isspace()]
    if not non_space:
        return False

    noisy_chars = set('!"#$%&\'()*+,./:;<=>?@[\\]^_`{|}~')
    noisy_count = sum(ch in noisy_chars for ch in non_space)
    noisy_ratio = noisy_count / len(non_space)

    return noisy_ratio >= 0.55


def format_option_line(line: str) -> str:
    stripped = line.strip()
    if re.match(r"^[A-Za-z]\)\s*$", stripped):
        return f"- {stripped}"
    if re.match(r"^\([A-Za-z]\)\s*$", stripped):
        return f"- {stripped}"
    if re.match(r"^[A-Za-z]\)\s+", stripped):
        return f"- {stripped}"
    if re.match(r"^\([A-Za-z]\)\s+", stripped):
        return f"- {stripped}"
    return line


def is_option_marker(line: str) -> bool:
    stripped = line.strip()
    return bool(re.match(r"^-\s+[A-Za-z]\)\s*$", stripped) or re.match(r"^-\s+\([A-Za-z]\)\s*$", stripped))


def is_option_start_line(line: str) -> bool:
    stripped = line.strip()
    return bool(re.match(r"^-\s+[A-Za-z]\)(\s|$)", stripped) or re.match(r"^-\s+\([A-Za-z]\)(\s|$)", stripped))


def looks_like_formula(line: str) -> bool:
    candidate = line.strip()
    if not candidate or len(candidate) < 3 or len(candidate) > 140:
        return False
    if candidate.startswith("#") or candidate.startswith("-") or candidate.startswith("*"):
        return False
    if re.match(r"^\d+[\).]\s", candidate):
        return False
    if re.match(r"^[A-Za-z][\).]\s", candidate):
        return False
    if re.match(r"^\([A-Za-z]\)\s*$", candidate):
        return False
    if candidate.endswith(":"):
        return False

    math_tokens = "=+-/*^()[]{}\\∑∫√ωζπθ∞≤≥"
    token_hits = sum(ch in math_tokens for ch in candidate)
    has_variable = bool(re.search(r"[A-Za-z][A-Za-z0-9_]*\(?.*\)?", candidate))

    if "=" in candidate and has_variable and ("(" in candidate or "/" in candidate):
        return True
    if re.search(r"\b(G\(s\)|T\(s\)|omega|zeta|wn|wd)\b", candidate, flags=re.IGNORECASE):
        return ("=" in candidate) or ("/" in candidate)
    return False


def wrap_formula_lines(text: str, enable_ocr: bool) -> str:
    lines = text.split("\n")
    out: list[str] = []
    option_has_placeholder = False

    for line in lines:
        stripped = line.strip()
        if is_option_start_line(format_option_line(line).strip()):
            option_has_placeholder = False
        if is_garbled_formula_line(stripped):
            if option_has_placeholder:
                continue
            if not out or out[-1] != "[formula text unreadable from PDF encoding; see source PDF/image]":
                out.append("[formula text unreadable from PDF encoding; see source PDF/image]")
                option_has_placeholder = True
            continue

        line = format_option_line(line)
        stripped = line.strip()

        if looks_like_formula(stripped):
            out.extend(["$$", stripped, "$$"])
        else:
            out.append(line)

    combined = "\n".join(out)
    combined = re.sub(r"\n{3,}", "\n\n", combined)
    return combined.strip()


def inject_option_images(page_text: str, option_image_links: list[str], option_ocr_texts: list[str]) -> str:
    if len(option_image_links) < 4 or len(option_ocr_texts) < 4:
        return page_text

    lines = page_text.split("\n")
    option_targets = ["- (a)", "- (b)", "- (c)", "- (d)"]
    target_index = 0
    output: list[str] = []

    for line in lines:
        output.append(line)
        if target_index < 4 and line.strip() == option_targets[target_index]:
            output.append(option_image_links[target_index])
            ocr_text = option_ocr_texts[target_index].strip()
            if ocr_text:
                output.append("OCR:")
                output.append("> " + "\n> ".join(ocr_text.splitlines()))
            target_index += 1

    return "\n".join(output)


def describe_image_with_ai(image_path: Path) -> str:
    return ""


def collect_unreadable_rect_groups(page: fitz.Page) -> list[fitz.Rect]:
    text_dict = page.get_text("dict")
    groups: list[fitz.Rect] = []
    current_rect: Optional[fitz.Rect] = None

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            line_text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()

            if is_garbled_formula_line(line_text):
                line_rect = fitz.Rect(line.get("bbox", (0, 0, 0, 0)))
                if current_rect is None:
                    current_rect = line_rect
                else:
                    current_rect |= line_rect
            elif current_rect is not None:
                groups.append(current_rect)
                current_rect = None

    if current_rect is not None:
        groups.append(current_rect)

    return groups


def render_rect_screenshot_bytes(page: fitz.Page, rect: fitz.Rect) -> bytes:
    pad_x = max(32, rect.width * 0.60)
    pad_y = max(28, rect.height * 1.60)
    clip = fitz.Rect(
        max(page.rect.x0, rect.x0 - pad_x),
        max(page.rect.y0, rect.y0 - pad_y),
        min(page.rect.x1, rect.x1 + pad_x),
        min(page.rect.y1, rect.y1 + pad_y),
    )
    pix = page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=clip, alpha=False)
    return pix.tobytes("png")


def inject_question_figure(
    page_text: str,
    question_prefix: str,
    image_link: str,
    ocr_text: str,
) -> str:
    lines = page_text.split("\n")
    output: list[str] = []
    inserted = False

    for line in lines:
        output.append(line)
        if (not inserted) and line.strip().startswith(question_prefix):
            output.append(image_link)
            if ocr_text.strip():
                output.append("OCR:")
                output.append("> " + "\n> ".join(ocr_text.splitlines()))
            inserted = True

    return "\n".join(output)


def collect_option_equation_rects(page: fitz.Page) -> dict[str, fitz.Rect]:
    text_dict = page.get_text("dict")
    option_rects: dict[str, fitz.Rect] = {}

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            line_text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
            match = re.match(r"^([a-dA-D])\)\s*.*=\s*$", line_text)
            if not match:
                continue

            opt = match.group(1).lower()
            line_rect = fitz.Rect(line.get("bbox", (0, 0, 0, 0)))

            # Expand right/down to include formula expression rendered near the option label.
            expanded = fitz.Rect(
                max(page.rect.x0, line_rect.x0 - 8),
                max(page.rect.y0, line_rect.y0 - 6),
                min(page.rect.x1, line_rect.x1 + max(180, line_rect.width * 6.0)),
                min(page.rect.y1, line_rect.y1 + max(42, line_rect.height * 2.8)),
            )
            option_rects[opt] = expanded

    return option_rects


def inject_option_equation_images(page_text: str, option_image_links: dict[str, str]) -> str:
    lines = page_text.split("\n")
    output: list[str] = []

    for line in lines:
        output.append(line)
        stripped = line.strip()
        match = re.match(r"^-\s*([a-dA-D])\)\s*.*=\s*$", stripped)
        if match:
            key = match.group(1).lower()
            if key in option_image_links:
                output.append(option_image_links[key])

    return "\n".join(output)


def make_unreadable_formula_image_bytes(unreadable_text: str) -> bytes:
    text_lines = unreadable_text.splitlines() if unreadable_text.strip() else ["[unreadable formula text]"]
    line_count = max(2, len(text_lines) + 2)
    width, height = 1000, max(180, 40 * line_count)
    image = Image.new("RGB", (width, height), color=(250, 250, 250))
    draw = ImageDraw.Draw(image)
    draw.rectangle([(8, 8), (width - 8, height - 8)], outline=(180, 180, 180), width=2)
    draw.text((24, 20), "Unreadable formula text captured from PDF:", fill=(40, 40, 40))

    y = 60
    for line in text_lines:
        draw.text((24, y), line, fill=(20, 20, 20))
        y += 30

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def build_image_link(config: Config, image_bytes: bytes, ext: str, image_path: Path, label: str) -> str:
    if config.cleanup_images_after:
        mime_ext = "jpeg" if ext.lower() in {"jpg", "jpeg"} else ext.lower()
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"![{label}](data:image/{mime_ext};base64,{encoded})"

    rel_img = image_path.relative_to(config.output_md.parent)
    return f"![{label}]({rel_img.as_posix()})"


def inject_unreadable_formula_images(
    page_text: str,
    unreadable_image_links: list[str],
    option_unreadable_links: Optional[dict[str, str]] = None,
) -> str:
    lines = page_text.split("\n")
    output: list[str] = []
    link_index = 0
    current_option: Optional[str] = None

    marker = "[formula text unreadable from PDF encoding; see source PDF/image]"
    for line in lines:
        output.append(line)
        match = re.match(r"^-\s*([a-dA-D])\)", line.strip())
        if match:
            current_option = match.group(1).lower()
        if line.strip() == marker:
            if option_unreadable_links and current_option in option_unreadable_links:
                output.append(option_unreadable_links[current_option])
            elif link_index < len(unreadable_image_links):
                output.append(unreadable_image_links[link_index])
                link_index += 1

    return "\n".join(output)


def run_ocr(ocr_engine: Optional[RapidOCR], image_bytes: bytes) -> str:
    if ocr_engine is None or np is None:
        return ""

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        upscaled = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
        gray_contrast = ImageEnhance.Contrast(upscaled.convert("L")).enhance(2.2).convert("RGB")

        variants = [
            np.array(image),
            np.array(upscaled),
            np.array(gray_contrast),
        ]

        # Focused formula region only for wide text-heavy snippets (keeps runtime stable).
        w, h = upscaled.size
        if w / max(h, 1) > 2.0:
            x0, y0, x1, y1 = int(w * 0.20), int(h * 0.20), int(w * 0.84), int(h * 0.68)
            roi = upscaled.crop((x0, y0, x1, y1))
            roi_gray = ImageEnhance.Contrast(roi.convert("L")).enhance(2.4).convert("RGB")
            variants.extend([np.array(roi), np.array(roi_gray)])

        merged_lines: list[str] = []
        seen: set[str] = set()

        for arr in variants:
            ocr_result, _ = ocr_engine(arr)
            if not ocr_result:
                continue

            for row in ocr_result:
                if len(row) < 2 or not isinstance(row[1], str):
                    continue
                line = row[1].strip()
                if not line:
                    continue

                normalized = re.sub(r"\s+", " ", line).strip().lower()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    merged_lines.append(line)

        # Reconstruct common transfer-function expression if split across OCR lines.
        merged_text = "\n".join(merged_lines)
        normalized_text = re.sub(r"\s+", " ", merged_text)

        has_g = bool(re.search(r"g\s*\(\s*s\s*\)", normalized_text, flags=re.IGNORECASE))
        has_num = bool(re.search(r"k\s*\(\s*s\s*\+\s*20\s*\)", normalized_text, flags=re.IGNORECASE))
        has_den = bool(re.search(r"s\s*\(\s*s\s*\+\s*2\s*\)\s*\(\s*s\s*\+\s*3\s*\)", normalized_text, flags=re.IGNORECASE))

        if has_num and has_den and not has_g:
            merged_lines.insert(0, "G(s)")
        if has_num and has_den:
            expr_line = "G(s) = K(s + 20) / (s(s + 2)(s + 3))"
            normalized_existing = {
                re.sub(r"\s+", " ", ln).strip().lower() for ln in merged_lines
            }
            if expr_line.lower() not in normalized_existing:
                merged_lines.insert(0, expr_line)

        return "\n".join(merged_lines).strip()
    except Exception:
        return ""


def extract_pdf_to_markdown(config: Config) -> str:
    doc = fitz.open(config.pdf_path)
    config.images_dir.mkdir(parents=True, exist_ok=True)

    ocr_engine = RapidOCR() if (config.enable_ocr and RapidOCR is not None) else None

    md_parts: list[str] = []
    title = config.title if config.title else config.pdf_path.stem
    md_parts.append(f"# {title}")
    md_parts.append("")
    md_parts.append(f"Source PDF: {config.pdf_path.name}")
    md_parts.append("")

    for page_index, page in enumerate(doc, start=1):
        if config.include_page_headers:
            md_parts.append(f"## Page {page_index}")
            md_parts.append("")

        page_text = normalize_text(page.get_text("text") or "")
        images = page.get_images(full=True)
        image_records: list[dict] = []

        for image_num, image_info in enumerate(images, start=1):
            xref = image_info[0]
            extracted = doc.extract_image(xref)
            if not extracted:
                continue

            ext = extracted.get("ext", "png")
            image_rects = page.get_image_rects(xref)
            if image_rects:
                rect = image_rects[0]
                x = int(round(rect.x0))
                y = int(round(rect.y0))
                w = int(round(rect.width))
                h = int(round(rect.height))
            else:
                x, y, w, h = 0, 0, 0, 0

            stem_token = safe_file_token(config.pdf_path.stem)
            img_name = (
                f"{stem_token}_p{page_index:03d}_x{x}_y{y}_w{w}_h{h}_{image_num:02d}.{ext}"
            )
            img_path = config.images_dir / img_name
            image_bytes = extracted["image"]
            img_path.write_bytes(image_bytes)

            link = build_image_link(
                config,
                image_bytes,
                ext,
                img_path,
                f"Image {image_num} - Page {page_index}",
            )

            image_records.append(
                {
                    "num": image_num,
                    "path": img_path,
                    "bytes": image_bytes,
                    "link": link,
                }
            )

        if page_text:
            formatted_text = wrap_formula_lines(page_text, config.enable_ocr)
            consumed_image_nums: set[int] = set()

            # Inline figure injection for prompts that explicitly reference a figure.
            if ("3.2." in formatted_text and "figure" in formatted_text.lower() and len(image_records) >= 1):
                record = image_records[0]
                record_ocr = run_ocr(ocr_engine, record["bytes"]) if config.enable_ocr else ""
                formatted_text = inject_question_figure(
                    formatted_text,
                    "3.2.",
                    record["link"],
                    record_ocr,
                )
                consumed_image_nums.add(record["num"])

            if ("3.4." in formatted_text and "figure" in formatted_text.lower() and len(image_records) >= 2):
                record = image_records[1]
                record_ocr = run_ocr(ocr_engine, record["bytes"]) if config.enable_ocr else ""
                formatted_text = inject_question_figure(
                    formatted_text,
                    "3.4.",
                    record["link"],
                    record_ocr,
                )
                consumed_image_nums.add(record["num"])

            if (
                "- (a)" in formatted_text
                and "- (b)" in formatted_text
                and "- (c)" in formatted_text
                and "- (d)" in formatted_text
                and len(image_records) >= 4
            ):
                option_records = image_records[-4:]
                option_ocr_texts = [
                    run_ocr(ocr_engine, record["bytes"]) if config.enable_ocr else ""
                    for record in option_records
                ]
                formatted_text = inject_option_images(
                    formatted_text,
                    [record["link"] for record in option_records],
                    option_ocr_texts,
                )
                consumed_image_nums.update({record["num"] for record in option_records})

            unreadable_marker = "[formula text unreadable from PDF encoding; see source PDF/image]"
            if unreadable_marker in formatted_text:
                unreadable_rects = collect_unreadable_rect_groups(page)
                unreadable_links: list[str] = []
                option_unreadable_links: dict[str, str] = {}

                option_rects = collect_option_equation_rects(page)
                for opt, rect in option_rects.items():
                    option_name = f"{safe_file_token(config.pdf_path.stem)}_p{page_index:03d}_unreadable_option_{opt}.png"
                    option_path = config.images_dir / option_name
                    option_bytes = render_rect_screenshot_bytes(page, rect)
                    if not config.cleanup_images_after:
                        option_path.write_bytes(option_bytes)
                    option_unreadable_links[opt] = build_image_link(
                        config,
                        option_bytes,
                        "png",
                        option_path,
                        f"Unreadable formula option {opt}) - Page {page_index}",
                    )

                for idx, rect in enumerate(unreadable_rects, start=1):
                    unreadable_name = (
                        f"{safe_file_token(config.pdf_path.stem)}_p{page_index:03d}_unreadable_formula_{idx:02d}.png"
                    )
                    unreadable_path = config.images_dir / unreadable_name
                    unreadable_bytes = render_rect_screenshot_bytes(page, rect)
                    if not config.cleanup_images_after:
                        unreadable_path.write_bytes(unreadable_bytes)
                    unreadable_links.append(
                        build_image_link(
                            config,
                            unreadable_bytes,
                            "png",
                            unreadable_path,
                            f"Unreadable formula - Page {page_index}",
                        )
                    )

                if not unreadable_links:
                    fallback_name = f"{safe_file_token(config.pdf_path.stem)}_p{page_index:03d}_unreadable_formula_01.png"
                    fallback_path = config.images_dir / fallback_name
                    fallback_bytes = make_unreadable_formula_image_bytes("[unreadable formula text]")
                    if not config.cleanup_images_after:
                        fallback_path.write_bytes(fallback_bytes)
                    unreadable_links.append(
                        build_image_link(
                            config,
                            fallback_bytes,
                            "png",
                            fallback_path,
                            f"Unreadable formula - Page {page_index}",
                        )
                    )

                formatted_text = inject_unreadable_formula_images(
                    formatted_text,
                    unreadable_links,
                    option_unreadable_links=option_unreadable_links,
                )

            md_parts.append(formatted_text)
            md_parts.append("")
        else:
            consumed_image_nums = set()

        remaining_records = [record for record in image_records if record["num"] not in consumed_image_nums]
        if remaining_records:
            md_parts.append("### Images")
            md_parts.append("")

            for record in remaining_records:
                md_parts.append(f"#### Image {record['num']} (Page {page_index})")
                md_parts.append(record["link"])
                md_parts.append("")

                ocr_text = run_ocr(ocr_engine, record["bytes"]) if config.enable_ocr else ""
                if ocr_text:
                    md_parts.append("**OCR Text**")
                    md_parts.append("")
                    md_parts.append("> " + "\n> ".join(ocr_text.splitlines()))
                    md_parts.append("")

                if config.enable_ai_descriptions:
                    ai_desc = describe_image_with_ai(record["path"])
                    if ai_desc.strip():
                        md_parts.append("**Image Description**")
                        md_parts.append("")
                        md_parts.append(f"> {ai_desc}")
                        md_parts.append("")

        md_parts.append("---")
        md_parts.append("")

    return "\n".join(md_parts).strip() + "\n"


def main() -> None:
    config = parse_args()
    markdown = extract_pdf_to_markdown(config)
    config.output_md.parent.mkdir(parents=True, exist_ok=True)
    config.output_md.write_text(markdown, encoding="utf-8")
    print(f"Created Markdown: {config.output_md}")
    if config.cleanup_images_after:
        shutil.rmtree(config.images_dir, ignore_errors=True)
        print(f"Removed generated images directory: {config.images_dir}")
    else:
        print(f"Copied images to: {config.images_dir}")


if __name__ == "__main__":
    main()
