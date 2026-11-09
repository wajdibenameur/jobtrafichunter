from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.document import DocumentInspection


class CvPrivatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    filename: str = Field(max_length=200, repr=False)
    content_type: str
    inspection: DocumentInspection = Field(repr=False)


class CvVersionView(BaseModel):
    id: UUID
    document_id: UUID
    number: int
    filename: str
    byte_size: int
    state: str
    analysis_status: str
    active: bool
    created_at: datetime


class CvVersionData(BaseModel):
    version: CvVersionView
    inspection: DocumentInspection = Field(repr=False)
