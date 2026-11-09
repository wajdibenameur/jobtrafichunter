import io
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject

from app.core.errors import AppError
from app.modules.ai import LocalDocumentInspector
from tests.document_fixtures import docx_fixture, pdf_fixture

RUNTIME = Path(__file__).resolve().parents[5] / ".cache/cv-sandbox"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows parser contract")
async def test_real_isolated_text_pdf_docx_and_scan_status(
    caplog: pytest.LogCaptureFixture,
) -> None:
    inspector = LocalDocumentInspector(RUNTIME)
    pdf = await inspector(pdf_fixture(), "synthetic.pdf", "application/pdf")
    assert pdf.status == "TEXT" and pdf.kind == "PDF"
    assert pdf.parser_version == "pypdf-7.0.0"
    assert "SYNTHETIC_CV_MARKER" in pdf.pages[0].text
    scan = await inspector(pdf_fixture(text=None), "scan.pdf", "application/pdf")
    assert scan.status == "NEEDS_OCR" and scan.pages[0].text == ""
    docx = await inspector(docx_fixture(), "synthetic.docx", DOCX)
    assert docx.status == "TEXT" and docx.kind == "DOCX"
    assert "études ملف" in docx.pages[0].text
    assert "SYNTHETIC_CV_MARKER" not in caplog.text
    assert "SYNTHETIC_CV_MARKER" not in repr(pdf)


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows parser contract")
async def test_real_inspection_rejects_active_malformed_and_unsupported_documents() -> None:
    inspector = LocalDocumentInspector(RUNTIME)
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(pdf_fixture())))
    writer._root_object[NameObject("/OpenAction")] = DictionaryObject(
        {
            NameObject("/S"): NameObject("/JavaScript"),
            NameObject("/JS"): TextStringObject("app.alert('SYNTHETIC_CV_MARKER')"),
        }
    )
    active = io.BytesIO()
    writer.write(active)
    cases = [
        (b"MZ synthetic exe", "renamed.pdf", "application/pdf", "CV_FORMAT_INVALID"),
        (pdf_fixture(), "renamed.docx", DOCX, "CV_FORMAT_INVALID"),
        (docx_fixture(), "renamed.pdf", "application/pdf", "CV_FORMAT_INVALID"),
        (active.getvalue(), "active.pdf", "application/pdf", "CV_UNSAFE_DOCUMENT"),
        (
            docx_fixture(extra={"word/vbaProject.bin": b"macro"}),
            "macro.docx",
            DOCX,
            "CV_UNSAFE_DOCUMENT",
        ),
        (
            docx_fixture(extra={"word/embeddings/object.bin": b"embedded"}),
            "embedded.docx",
            DOCX,
            "CV_UNSAFE_DOCUMENT",
        ),
        (
            docx_fixture(extra={"word/evil.xml": b'<!DOCTYPE x [<!ENTITY y "bad">]><x>&y;</x>'}),
            "entity.docx",
            DOCX,
            "CV_UNSAFE_DOCUMENT",
        ),
        (
            docx_fixture(extra={"../escape.xml": b"<x/>"}),
            "traversal.docx",
            DOCX,
            "CV_UNSAFE_DOCUMENT",
        ),
        (b"synthetic DOC", "legacy.doc", "application/msword", "CV_DOC_UNAVAILABLE"),
    ]
    for content, name, mime, code in cases:
        with pytest.raises(AppError) as error:
            await inspector(content, name, mime)
        assert error.value.code == code
        assert "SYNTHETIC_CV_MARKER" not in str(error.value)


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows parser contract")
async def test_real_inspection_rejects_encryption_and_zip_expansion_limit() -> None:
    inspector = LocalDocumentInspector(RUNTIME)
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(pdf_fixture())))
    writer.encrypt("synthetic-password")
    encrypted = io.BytesIO()
    writer.write(encrypted)
    with pytest.raises(AppError) as error:
        await inspector(encrypted.getvalue(), "encrypted.pdf", "application/pdf")
    assert error.value.code == "CV_ENCRYPTED_DOCUMENT"
    with pytest.raises(AppError) as expansion:
        await inspector(docx_fixture(extra={"word/large.xml": b"x" * 200000}), "bomb.docx", DOCX)
    assert expansion.value.code == "CV_DOCUMENT_LIMIT"
