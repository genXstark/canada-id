"""Province/territory profile registry.

Provides lookup by two-letter code or six-digit IIN.
"""

from __future__ import annotations

from canada_id.provinces.base import ProvinceProfile

# Lazy-loaded cache to avoid circular imports at module level.
_BY_CODE: dict[str, ProvinceProfile] = {}
_BY_IIN: dict[str, ProvinceProfile] = {}


def _load() -> None:
    """Import all province modules and populate lookup dicts."""
    if _BY_CODE:
        return
    from canada_id.provinces.ab import PROFILE as AB
    from canada_id.provinces.bc import PROFILE as BC
    from canada_id.provinces.mb import PROFILE as MB
    from canada_id.provinces.nb import PROFILE as NB
    from canada_id.provinces.nl import PROFILE as NL
    from canada_id.provinces.ns import PROFILE as NS
    from canada_id.provinces.nt import PROFILE as NT
    from canada_id.provinces.nu import PROFILE as NU
    from canada_id.provinces.on import PROFILE as ON
    from canada_id.provinces.pe import PROFILE as PE
    from canada_id.provinces.qc import PROFILE as QC
    from canada_id.provinces.sk import PROFILE as SK
    from canada_id.provinces.yt import PROFILE as YT

    for profile in [
        AB, BC, MB, NB, NL, NS, NT, NU, ON, PE, QC, SK, YT,
    ]:
        _BY_CODE[profile.code] = profile
        _BY_IIN[profile.iin] = profile


def get_profile(code: str) -> ProvinceProfile:
    """Look up a province profile by two-letter code.

    Args:
        code: Province/territory code (e.g. "ON", "BC").

    Returns:
        Matching ProvinceProfile.

    Raises:
        KeyError: If the code is not recognized.
    """
    _load()
    code = code.upper()
    if code not in _BY_CODE:
        raise KeyError(f"Unknown province code: {code!r}")
    return _BY_CODE[code]


def get_profile_by_iin(iin: str) -> ProvinceProfile:
    """Look up a province profile by IIN.

    Args:
        iin: Six-digit issuer identification number.

    Returns:
        Matching ProvinceProfile.

    Raises:
        KeyError: If the IIN is not recognized.
    """
    _load()
    if iin not in _BY_IIN:
        raise KeyError(f"Unknown IIN: {iin!r}")
    return _BY_IIN[iin]


def all_profiles() -> list[ProvinceProfile]:
    """Return all registered province profiles sorted by code.

    Returns:
        List of all 13 ProvinceProfile instances.
    """
    _load()
    return sorted(_BY_CODE.values(), key=lambda p: p.code)
