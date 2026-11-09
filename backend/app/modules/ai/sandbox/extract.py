"""Standalone parser: run only inside the verified AppContainer runtime.

This file deliberately imports no application modules or settings. Input/output
are bounded JSON pipes; no document is written to disk or fetched from a URL.
"""

import base64
import io
import json
import logging
import re
import sys
import zipfile
from pathlib import PurePosixPath
from xml.etree import ElementTree

from pypdf import PdfReader, __version__
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

MAX_BYTES = 5 * 1024 * 1024
MAX_TEXT = 50000
MAX_PAGES = 50
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class ParseError(Exception):
    pass


def xml(data: bytes) -> ElementTree.Element:
    if len(data) > 2 * 1024 * 1024:
        raise ParseError("CV_DOCUMENT_LIMIT")
    text = data.decode("utf-8-sig")
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ParseError("CV_UNSAFE_DOCUMENT")
    return ElementTree.fromstring(text)


def docx(data: bytes) -> list[str]:
    if data[:4] != b"PK\x03\x04":
        raise ParseError("CV_FORMAT_INVALID")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if not 1 <= len(entries) <= 500 or sum(e.file_size for e in entries) > 10 * 1024 * 1024:
            raise ParseError("CV_DOCUMENT_LIMIT")
        names = {e.filename for e in entries}
        if len(names) != len(entries):
            raise ParseError("CV_FORMAT_INVALID")
        for entry in entries:
            path = PurePosixPath(entry.filename)
            name = entry.filename.casefold()
            suffix = ".rels" if name.endswith(".rels") else path.suffix.lower()
            if (
                entry.flag_bits & 1
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in name
                or ":" in name
                or "vba" in name
                or "embeddings/" in name
                or "activex/" in name
                or (
                    not entry.is_dir()
                    and suffix
                    not in {
                        ".xml",
                        ".rels",
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".bmp",
                        ".tif",
                        ".tiff",
                    }
                )
            ):
                raise ParseError("CV_UNSAFE_DOCUMENT")
            if entry.file_size > max(1, entry.compress_size) * 100:
                raise ParseError("CV_DOCUMENT_LIMIT")
            # Read all parts for CRC verification and bounded XML/entity checks.
            part = archive.read(entry)
            if suffix in {".xml", ".rels"}:
                xml(part)
            elif part[:2] == b"MZ" or part[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
                raise ParseError("CV_UNSAFE_DOCUMENT")
        if not {"[Content_Types].xml", "_rels/.rels", "word/document.xml"} <= names:
            raise ParseError("CV_FORMAT_INVALID")
        types = xml(archive.read("[Content_Types].xml"))
        if not any(
            item.get("PartName") == "/word/document.xml"
            and item.get("ContentType") == DOCX_MIME.replace(".document", ".document.main+xml")
            for item in types
        ):
            raise ParseError("CV_FORMAT_INVALID")
        relationships = xml(archive.read("_rels/.rels"))
        if not any(
            item.get("Type", "").endswith("/officeDocument")
            and item.get("Target") == "word/document.xml"
            and item.get("TargetMode") != "External"
            for item in relationships
        ):
            raise ParseError("CV_FORMAT_INVALID")
        document = xml(archive.read("word/document.xml"))
        if document.tag != WORD + "document":
            raise ParseError("CV_FORMAT_INVALID")
        if any(
            e.tag in {WORD + "object", WORD + "control", WORD + "altChunk"} for e in document.iter()
        ):
            raise ParseError("CV_UNSAFE_DOCUMENT")
        paragraphs = [
            "".join(t.text or "" for t in p.iter(WORD + "t")) for p in document.iter(WORD + "p")
        ]
        # Text nodes only: field instructions/macros are never executed or used as facts.
        return ["\n".join(paragraphs)]


def pdf(data: bytes) -> list[str]:
    if not re.match(rb"%PDF-(?:1\.[0-7]|2\.0)", data[:8]):
        raise ParseError("CV_FORMAT_INVALID")
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted:
        raise ParseError("CV_ENCRYPTED_DOCUMENT")
    if not 1 <= len(reader.pages) <= MAX_PAGES:
        raise ParseError("CV_DOCUMENT_LIMIT")
    pending: list[tuple[object, int]] = [(reader.trailer, 0)]
    seen: set[tuple[int, int]] = set()
    visited = 0
    prohibited_keys = {
        "/JS",
        "/JavaScript",
        "/Launch",
        "/EmbeddedFile",
        "/EmbeddedFiles",
        "/EF",
        "/XFA",
        "/RichMedia",
        "/OpenAction",
        "/AA",
        "/AcroForm",
    }
    prohibited_actions = {
        "/JavaScript",
        "/Launch",
        "/GoToR",
        "/GoToE",
        "/SubmitForm",
        "/ImportData",
        "/Rendition",
        "/RichMediaExecute",
        "/Sound",
        "/Movie",
    }
    while pending:
        value, depth = pending.pop()
        visited += 1
        if visited > 50000 or depth > 50:
            raise ParseError("CV_DOCUMENT_LIMIT")
        if isinstance(value, IndirectObject):
            key = (value.idnum, value.generation)
            if key in seen:
                continue
            seen.add(key)
            value = value.get_object()
        if isinstance(value, DictionaryObject):
            if any(str(key) in prohibited_keys for key in value):
                raise ParseError("CV_UNSAFE_DOCUMENT")
            if (
                str(value.get("/S")) in prohibited_actions
                or str(value.get("/Type")) == "/EmbeddedFile"
            ):
                raise ParseError("CV_UNSAFE_DOCUMENT")
            pending.extend((child, depth + 1) for child in value.values())
        elif isinstance(value, ArrayObject):
            pending.extend((child, depth + 1) for child in value)
    return [page.extract_text() for page in reader.pages]


def main() -> None:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.disable(logging.CRITICAL)
    try:
        request = json.loads(sys.stdin.buffer.read(8 * 1024 * 1024))
        data = base64.b64decode(request["content"], validate=True)
        if not 1 <= len(data) <= MAX_BYTES:
            raise ParseError("CV_SIZE_INVALID")
        extension = PurePosixPath(request["filename"]).suffix.lower()
        mime = request["content_type"]
        if extension == ".doc":
            raise ParseError("CV_DOC_UNAVAILABLE")
        if extension == ".pdf" and mime == "application/pdf":
            pages, kind = pdf(data), "PDF"
        elif extension == ".docx" and mime == DOCX_MIME:
            pages, kind = docx(data), "DOCX"
        else:
            raise ParseError("CV_FORMAT_INVALID")
        if sum(map(len, pages)) > MAX_TEXT:
            raise ParseError("CV_DOCUMENT_LIMIT")
        result = {
            "status": "TEXT" if any(p.strip() for p in pages) else "NEEDS_OCR",
            "kind": kind,
            "parser_version": "pypdf-" + __version__ if kind == "PDF" else "docx-xml-v1",
            "pages": [{"number": n, "text": text} for n, text in enumerate(pages, start=1)],
        }
    except ParseError as error:
        result = {"error": str(error)}
    except Exception:
        # Never forward library diagnostics, filenames or document fragments.
        result = {"error": "CV_FORMAT_INVALID"}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
