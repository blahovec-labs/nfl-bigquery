"""Shared Norton Antivirus SSL session patch for Windows nflreadpy downloads.

Norton AV intercepts HTTPS with a MITM root CA whose BasicConstraints extension
is not marked critical — OpenSSL 3.0 rejects this by default.  This module
patches the global nflreadpy downloader session so nflverse data loads work on
Windows machines protected by Norton Web/Mail Shield.

Certificate *chain* verification remains fully ON.  Only the strict
RFC-5280 BasicConstraints-critical requirement is relaxed.
"""
from __future__ import annotations

import platform
import ssl

import certifi
import requests
from requests.adapters import HTTPAdapter


def _build_norton_ssl_context() -> ssl.SSLContext:
    """Return an SSL context that accepts Norton Antivirus MITM CA certs.

    Norton's root CA has BasicConstraints not marked critical, which OpenSSL 3.0
    rejects by default.  We:
      1. Start from certifi's known-good CA bundle.
      2. Append the Norton Web/Mail Shield Root cert from the Windows cert store.
      3. Clear VERIFY_X509_STRICT so OpenSSL 3.0 does NOT enforce the critical flag.

    Certificate chain verification (that the presented cert is signed by a known CA)
    remains fully ON.  Only the strict RFC-5280 BasicConstraints-critical requirement
    is relaxed.
    """
    import base64

    ctx = ssl.create_default_context(cafile=certifi.where())

    # Locate Norton's MITM CA in the Windows root store and load it.
    added = 0
    for store in ("ROOT",):
        for cert_data, enc_type, _trust in ssl.enum_certificates(store):  # type: ignore[attr-defined]
            if enc_type != "x509_asn":
                continue
            try:
                from cryptography import x509
                from cryptography.hazmat.backends import default_backend

                cert = x509.load_der_x509_certificate(cert_data, default_backend())
                subj = cert.subject.rfc4514_string()
            except Exception:
                continue
            if "Norton Web/Mail Shield Root" in subj:
                b64 = base64.b64encode(cert_data).decode()
                lines = [b64[i : i + 64] for i in range(0, len(b64), 64)]
                pem = (
                    "-----BEGIN CERTIFICATE-----\n"
                    + "\n".join(lines)
                    + "\n-----END CERTIFICATE-----\n"
                )
                ctx.load_verify_locations(cadata=pem)
                added += 1

    if added == 0:
        raise RuntimeError("Norton Web/Mail Shield Root not found in Windows cert store")

    # Disable the strict RFC-5280 BasicConstraints-critical check; chain-of-trust
    # verification is still fully active.
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT  # type: ignore[attr-defined]
    return ctx


class _NortonCompatAdapter(HTTPAdapter):
    """HTTPS adapter that uses an SSL context tolerating Norton MITM CA certs."""

    def __init__(self, ssl_ctx: ssl.SSLContext, *args: object, **kwargs: object) -> None:
        self._ssl_ctx = ssl_ctx
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    def init_poolmanager(self, *args: object, **kwargs: object) -> None:
        kwargs["ssl_context"] = self._ssl_ctx  # type: ignore[assignment]
        super().init_poolmanager(*args, **kwargs)  # type: ignore[arg-type]


def patch_nflreadpy_session_if_windows() -> None:
    """Replace the global nflreadpy downloader session with a Norton-compatible one.

    No-op on non-Windows platforms.  On Windows, mounts a Norton-tolerant HTTPS
    adapter so that nflverse data downloads succeed through Norton Web/Mail Shield.

    Chain-of-trust verification remains fully ON; only the strict
    RFC-5280 BasicConstraints-critical requirement is relaxed.

    Raises:
        RuntimeError: if Norton Web/Mail Shield Root is not found in the
            Windows certificate store (Windows only).
    """
    if platform.system() != "Windows":
        return

    import nflreadpy.downloader as _ndl  # local import — optional dep at call site

    ctx = _build_norton_ssl_context()
    sess = requests.Session()
    sess.mount("https://", _NortonCompatAdapter(ctx))
    sess.mount("http://", HTTPAdapter())
    _ndl._downloader.session = sess  # type: ignore[assignment]
