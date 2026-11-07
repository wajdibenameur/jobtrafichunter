import csv
import io

from pydantic import ValidationError

from app.core.errors import AppError
from app.modules.listings.schemas import CsvPreview, ImportJob, PreviewRow

ALIASES = {
    "url": "original_url",
    "lien": "original_url",
    "titre": "title",
    "entreprise": "company",
    "pays": "country",
    "ville": "city",
    "publication": "published_at",
}


def preview_csv(text: str) -> CsvPreview:
    try:
        text = text.lstrip("\ufeff")
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    try:
        reader = csv.DictReader(io.StringIO(text), dialect=dialect, strict=True)
        headers = [
            ALIASES.get(field.strip().casefold(), field.strip().casefold())
            for field in (reader.fieldnames or [])
        ]
        if (
            not headers
            or "original_url" not in headers
            or len(headers) != len(set(headers))
            or any(header not in ImportJob.model_fields for header in headers)
        ):
            raise AppError(
                "CSV_HEADERS", "CSV requires a URL column and supported unique headers", 422
            )
        rows: list[PreviewRow] = []
        for row_number, row in enumerate(reader, start=2):
            if len(rows) >= 200:
                raise AppError("CSV_ROW_LIMIT", "At most 200 rows may be imported at once", 422)
            if None in row or any(value is None for value in row.values()):
                rows.append(PreviewRow(row_number=row_number, job=None, errors=["ROW_COLUMNS"]))
                continue
            values = {
                header: value.strip()
                for header, value in zip(headers, row.values(), strict=True)
                if value.strip()
            }
            try:
                job = ImportJob.model_validate(values)
                rows.append(PreviewRow(row_number=row_number, job=job, errors=[]))
            except ValidationError as exc:
                errors = sorted(
                    {
                        str(error["loc"][0]) if error["loc"] else "requirements"
                        for error in exc.errors(include_input=False)
                    }
                )
                rows.append(PreviewRow(row_number=row_number, job=None, errors=errors))
        if not rows:
            raise AppError("CSV_EMPTY", "CSV has no offer rows", 422)
        valid = sum(row.job is not None for row in rows)
        return CsvPreview(rows=rows, valid_count=valid, invalid_count=len(rows) - valid)
    except csv.Error as exc:
        raise AppError("CSV_INVALID", "CSV format is invalid", 422) from exc
