"""Local document-analysis interfaces. No hosted provider is enabled."""

from app.modules.ai.inspection import LocalDocumentInspector
from app.modules.ai.taxonomy import SkillDefinition, TaxonomyService

__all__ = ["LocalDocumentInspector", "SkillDefinition", "TaxonomyService"]
