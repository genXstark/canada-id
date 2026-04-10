"""Canadian province/territory profiles for AAMVA compliance."""

from canada_id.provinces.base import ProvinceProfile
from canada_id.provinces.registry import (
    all_profiles,
    get_profile,
    get_profile_by_iin,
)

__all__ = [
    "ProvinceProfile",
    "all_profiles",
    "get_profile",
    "get_profile_by_iin",
]
