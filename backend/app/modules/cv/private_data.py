from pydantic import SecretStr

from app.core.private_payload import PrivatePayload


class PrivateCvData(PrivatePayload):
    """Compatible facade: existing CV ciphertext and derivation remain unchanged."""

    def __init__(self, key: SecretStr) -> None:
        super().__init__(
            key,
            namespace=b"jobhunter/cv/private-db/v1/",
            magic=b"JHDB\x01",
            limit_code="CV_DATA_LIMIT",
            integrity_code="CV_INTEGRITY_FAILED",
            limit_message="Private CV data limit exceeded",
            integrity_message="Private CV data integrity failed",
        )
