"""Local document-analysis interfaces. No hosted provider is enabled."""

from app.modules.ai.inspection import LocalDocumentInspector
from app.modules.ai.job_analysis import (
    JobAnalysis,
    JobAnalysisService,
    JobEvidence,
    JobInput,
    aliases,
    analyze_job,
    content_hash,
)
from app.modules.ai.taxonomy import SkillDefinition, TaxonomyService

__all__ = [
    "LocalDocumentInspector",
    "SkillDefinition",
    "TaxonomyService",
    "JobInput",
    "JobAnalysis",
    "JobAnalysisService",
    "JobEvidence",
    "analyze_job",
    "aliases",
    "content_hash",
]
