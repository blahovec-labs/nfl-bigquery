"""Generate small parquet fixtures from nflverse for offline unit tests.

pbp: one game from 2023. schedules: 2023 week 1. players: first 50.
player_stats: 2023 week 1. Run: `python scripts/make_fixtures.py`.
"""
from __future__ import annotations

import platform
import ssl
from pathlib import Path

import certifi
import nflreadpy as nfl
import nflreadpy.downloader as _ndl
import requests
from requests.adapters import HTTPAdapter

OUT = Path("tests/fixtures")


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


def _patch_nflreadpy_session() -> None:
    """Replace the global nflreadpy downloader session with a Norton-compatible one."""
    ctx = _build_norton_ssl_context()
    sess = requests.Session()
    sess.mount("https://", _NortonCompatAdapter(ctx))
    sess.mount("http://", HTTPAdapter())
    _ndl._downloader.session = sess  # type: ignore[assignment]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    if platform.system() == "Windows":
        _patch_nflreadpy_session()

    pbp = nfl.load_pbp([2023]).to_pandas()
    one_game = pbp["game_id"].dropna().iloc[0]
    pbp[pbp["game_id"] == one_game].to_parquet(OUT / "pbp_2023_sample.parquet")

    sched = nfl.load_schedules([2023]).to_pandas()
    sched[sched["week"] == 1].to_parquet(OUT / "schedules_2023_sample.parquet")

    players = nfl.load_players().to_pandas().head(50)
    players.to_parquet(OUT / "players_2023_sample.parquet")

    stats = nfl.load_player_stats([2023]).to_pandas()
    stats[stats["week"] == 1].to_parquet(OUT / "player_stats_2023_sample.parquet")
    print("fixtures written")


if __name__ == "__main__":
    main()
