"""Private immutable CV storage; parsing and HTTP ingestion are separate gates."""

from app.modules.cv.vault import CvBlob, CvVault, VaultIdentity

__all__ = ["CvBlob", "CvVault", "VaultIdentity"]
