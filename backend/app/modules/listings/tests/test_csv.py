import pytest
from pydantic import ValidationError

from app.core.errors import AppError
from app.modules.listings.csv_import import preview_csv
from app.modules.listings.schemas import ImportJob, ImportRequest


def test_csv_aliases_quoted_multiline_and_unknown_values() -> None:
    result = preview_csv(
        "lien;titre;entreprise;description\n"
        'https://example.test/job;Python;Company;"Line one\nLine two"\n'
    )
    assert result.valid_count == 1 and result.invalid_count == 0
    job = result.rows[0].job
    assert job is not None and job.title == "Python"
    assert job.description == "Line one\nLine two"
    assert job.published_at is None and job.visa_status == "NOT_SPECIFIED"


def test_csv_reports_row_errors_without_echoing_content() -> None:
    result = preview_csv(
        "url,title\nhttps://example.test/1,Valid\njavascript:private-token,Invalid\n"
    )
    assert result.valid_count == 1 and result.invalid_count == 1
    assert result.rows[1].row_number == 3
    assert result.rows[1].errors == ["original_url"]
    assert "private-token" not in result.model_dump_json()


@pytest.mark.parametrize(
    "text", ["title\nJob", "url,url\nhttps://example.test/1,https://example.test/2", "url\n"]
)
def test_missing_duplicate_headers_and_empty_csv_rejected(text: str) -> None:
    with pytest.raises(AppError):
        preview_csv(text)


def test_csv_row_limit_is_explicit() -> None:
    text = "url\n" + "\n".join(f"https://example.test/{index}" for index in range(201))
    with pytest.raises(AppError) as error:
        preview_csv(text)
    assert error.value.code == "CSV_ROW_LIMIT"


@pytest.mark.parametrize(
    "values",
    [
        {"visa_status": "CONFIRMED"},
        {"min_years": 5, "max_years": 2},
        {"published_at": "2026-11-07T12:00:00"},
        {"original_url": "https://example.test/" + "x" * 2100},
    ],
)
def test_unknown_visa_and_invalid_requirements_never_invent_evidence(
    values: dict[str, object],
) -> None:
    payload: dict[str, object] = {"original_url": "https://example.test/job"}
    payload.update(values)
    with pytest.raises(ValidationError):
        ImportJob.model_validate(payload)


def test_import_requires_explicit_confirmation() -> None:
    with pytest.raises(ValidationError):
        ImportRequest.model_validate(
            {
                "source_id": "10000000-0000-4000-8000-000000000001",
                "jobs": [{"original_url": "https://example.test/job"}],
            }
        )
