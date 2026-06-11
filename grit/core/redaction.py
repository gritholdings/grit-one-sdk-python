from __future__ import annotations
import io
import logging
import os
import re
from dataclasses import dataclass, field
logger = logging.getLogger(__name__)
PDF_EXTENSIONS = {'pdf'}
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'tif', 'tiff', 'bmp'}
PII_ENTITY_TYPES = ('SSN',)
MIN_CONFIDENCE = 0.5
MAX_PDF_PAGES = 50
COMPREHEND_LANGUAGE_CODE = 'en'
SSN_REGEX = re.compile(r'(?<!\d)\d{3}[-\s]\d{2}[-\s]\d{4}(?!\d)')
@dataclass(frozen=True)


class BoundingBox:
    left: float
    top: float
    width: float
    height: float
@dataclass(frozen=True)


class Word:
    text: str
    box: BoundingBox
@dataclass(frozen=True)


class Span:
    begin: int
    end: int
@dataclass


class RedactionResult:
    content: bytes
    status: str
    entities_redacted: int = 0
    pages_processed: int = 0
    detail: dict = field(default_factory=dict)


def redact_file(content: bytes, *, filename: str,
                content_type: str | None = None) -> RedactionResult:
    try:
        return _redact_dispatch(content, filename=filename, content_type=content_type)
    except Exception:
        logger.warning(
            "PII redaction failed for %r; keeping the original UNREDACTED file "
            "(fail-open).", filename, exc_info=True,
        )
        return RedactionResult(content, status='failed')


def _redact_dispatch(content: bytes, *, filename: str,
                     content_type: str | None) -> RedactionResult:
    extension = os.path.splitext(filename)[1].lower().lstrip('.')
    if extension in PDF_EXTENSIONS or content_type == 'application/pdf':
        return _redact_pdf(content)
    if extension in IMAGE_EXTENSIONS or (content_type or '').startswith('image/'):
        return _redact_image(content)
    return RedactionResult(content, status='skipped',
                           detail={'reason': 'unsupported_type',
                                   'extension': extension})


def find_ssn_spans_regex(text: str) -> list[Span]:
    return [Span(match.start(), match.end()) for match in SSN_REGEX.finditer(text)]


def find_pii_spans_comprehend(text: str, *, client=None) -> list[Span]:
    if not text.strip():
        return []
    if client is None:
        from grit.core.utils.aws.s3 import create_session
        client = create_session().client('comprehend')
    entity_types = set(PII_ENTITY_TYPES)
    response = client.detect_pii_entities(Text=text, LanguageCode=COMPREHEND_LANGUAGE_CODE)
    spans: list[Span] = []
    for entity in response.get('Entities', []):
        if entity.get('Type') not in entity_types:
            continue
        if float(entity.get('Score', 0.0)) < MIN_CONFIDENCE:
            continue
        spans.append(Span(int(entity['BeginOffset']), int(entity['EndOffset'])))
    return spans


def detect_pii_spans(text: str, *, comprehend_client=None) -> list[Span]:
    spans = find_ssn_spans_regex(text)
    try:
        spans = spans + find_pii_spans_comprehend(text, client=comprehend_client)
    except Exception:
        logger.warning(
            "AWS Comprehend PII detection failed; falling back to regex-only "
            "SSN detection.", exc_info=True,
        )
    return _merge_spans(spans)


def _merge_spans(spans: list[Span]) -> list[Span]:
    if not spans:
        return []
    ordered = sorted(spans, key=lambda span: (span.begin, span.end))
    merged = [ordered[0]]
    for span in ordered[1:]:
        last = merged[-1]
        if span.begin <= last.end:
            merged[-1] = Span(last.begin, max(last.end, span.end))
        else:
            merged.append(span)
    return merged


def extract_words(image_bytes: bytes, *, client=None) -> list[Word]:
    if client is None:
        from grit.core.utils.aws.s3 import create_session
        client = create_session().client('textract')
    response = client.detect_document_text(Document={'Bytes': image_bytes})
    words: list[Word] = []
    for block in response.get('Blocks', []):
        if block.get('BlockType') != 'WORD':
            continue
        bbox = block['Geometry']['BoundingBox']
        words.append(Word(
            text=block.get('Text', ''),
            box=BoundingBox(
                left=float(bbox['Left']), top=float(bbox['Top']),
                width=float(bbox['Width']), height=float(bbox['Height']),
            ),
        ))
    return words


def build_text_and_offsets(words: list[Word], *, joiner: str = ' '
                           ) -> tuple[str, list[tuple[int, int]]]:
    text_parts: list[str] = []
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for index, word in enumerate(words):
        if index > 0:
            cursor += len(joiner)
        start = cursor
        end = start + len(word.text)
        offsets.append((start, end))
        text_parts.append(word.text)
        cursor = end
    return joiner.join(text_parts), offsets


def words_overlapping_spans(offsets: list[tuple[int, int]],
                            spans: list[Span]) -> list[int]:
    hits: list[int] = []
    for index, (word_start, word_end) in enumerate(offsets):
        for span in spans:
            if word_start < span.end and span.begin < word_end:
                hits.append(index)
                break
    return hits


def redact_image_boxes(image_bytes: bytes, boxes: list[BoundingBox], *,
                       output_format: str | None = None) -> bytes:
    if not boxes:
        return image_bytes
    from PIL import Image, ImageDraw
    with Image.open(io.BytesIO(image_bytes)) as image:
        source_format = (output_format or image.format or 'PNG').upper()
        canvas = image.convert('RGB')
        width, height = canvas.size
        draw = ImageDraw.Draw(canvas)
        for box in boxes:
            left = int(box.left * width)
            top = int(box.top * height)
            right = int((box.left + box.width) * width)
            bottom = int((box.top + box.height) * height)
            draw.rectangle((left, top, right, bottom), fill=(0, 0, 0))
        save_format = 'JPEG' if source_format in {'JPEG', 'JPG'} else 'PNG'
        buffer = io.BytesIO()
        canvas.save(buffer, format=save_format)
        return buffer.getvalue()


def _true_redact_page_strings(page, strings) -> int:
    redacted = 0
    for needle in strings:
        if not needle or not needle.strip():
            continue
        for rectangle in page.search_for(needle):
            page.add_redact_annot(rectangle, fill=(0, 0, 0))
            redacted += 1
    if redacted:
        page.apply_redactions()
    return redacted


def _render_page_to_png(page, *, zoom: float = 2.0) -> bytes:
    import fitz
    pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    return pixmap.tobytes('png')


def _replace_page_with_png(document, page_index: int, png_bytes: bytes) -> None:
    rectangle = document[page_index].rect
    document.delete_page(page_index)
    new_page = document.new_page(pno=page_index, width=rectangle.width,
                                 height=rectangle.height)
    new_page.insert_image(rectangle, stream=png_bytes)


def _redact_image(content: bytes) -> RedactionResult:
    words = extract_words(_as_textract_image(content))
    text, offsets = build_text_and_offsets(words)
    spans = detect_pii_spans(text)
    if not spans:
        return RedactionResult(content, status='clean', pages_processed=1)
    boxes = [words[i].box for i in words_overlapping_spans(offsets, spans)]
    redacted = redact_image_boxes(content, boxes)
    return RedactionResult(redacted, status='redacted',
                           entities_redacted=len(spans), pages_processed=1)


def _as_textract_image(content: bytes) -> bytes:
    from PIL import Image
    with Image.open(io.BytesIO(content)) as image:
        if (image.format or '').upper() in {'PNG', 'JPEG'}:
            return content
        buffer = io.BytesIO()
        image.convert('RGB').save(buffer, format='PNG')
        return buffer.getvalue()


def _redact_pdf(content: bytes) -> RedactionResult:
    import fitz
    max_pages = MAX_PDF_PAGES
    entities = 0
    had_page_error = False
    total_pages = 0
    pages_to_process = 0
    output = content
    document = fitz.open(stream=content, filetype='pdf')
    try:
        total_pages = document.page_count
        pages_to_process = (min(total_pages, max_pages)
                            if max_pages > 0 else total_pages)
        for index in range(pages_to_process):
            try:
                entities += _redact_pdf_page(document, index)
            except Exception:
                had_page_error = True
                logger.warning(
                    "PII redaction failed on PDF page %d; it is kept "
                    "UNREDACTED.", index, exc_info=True,
                )
        output = document.tobytes()
    finally:
        document.close()
    detail: dict = {}
    pages_skipped = total_pages - pages_to_process
    if pages_skipped > 0:
        detail['pages_skipped'] = pages_skipped
        logger.warning(
            "PDF has %d page(s) but MAX_PDF_PAGES=%d; %d page(s) were not "
            "scanned and are kept UNREDACTED.",
            total_pages, max_pages, pages_skipped,
        )
    if had_page_error or pages_skipped > 0:
        status = 'partial'
        detail['reason'] = 'page_error' if had_page_error else 'page_cap'
    elif entities:
        status = 'redacted'
    else:
        status = 'clean'
    return RedactionResult(output, status=status, entities_redacted=entities,
                           pages_processed=pages_to_process, detail=detail)


def _redact_pdf_page(document, index: int) -> int:
    page = document[index]
    text = page.get_text("text")
    if text and text.strip():
        spans = detect_pii_spans(text)
        strings = {text[span.begin:span.end] for span in spans}
        return _true_redact_page_strings(page, strings)
    png = _render_page_to_png(page)
    words = extract_words(png)
    page_text, offsets = build_text_and_offsets(words)
    spans = detect_pii_spans(page_text)
    if not spans:
        return 0
    boxes = [words[i].box for i in words_overlapping_spans(offsets, spans)]
    redacted_png = redact_image_boxes(png, boxes)
    _replace_page_with_png(document, index, redacted_png)
    return len(spans)
