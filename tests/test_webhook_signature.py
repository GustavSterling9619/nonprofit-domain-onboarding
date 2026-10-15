import hashlib
import hmac

from nonprofit_domains.service import verify_signature


def test_verification_signature_accepts_the_exact_body() -> None:
    body = b'{"event":"dns.domain.verified","data":{"domain":"give.rivertown.example"}}'
    secret = "a-local-test-secret"
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert verify_signature(body, f"sha256={signature}", secret)
    assert not verify_signature(body + b" ", f"sha256={signature}", secret)
