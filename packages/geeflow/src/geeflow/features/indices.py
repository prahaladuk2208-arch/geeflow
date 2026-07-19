"""Config-driven spectral index registry.

Every builder works on harmonized band names (Blue, Green, Red, NIR, SWIR1, SWIR2,
RedEdge1, ...). An index is only computed when all its required bands exist in the
image, so band-poor eras (e.g. MSS without Blue/SWIR) automatically get the subset
that is physically computable — nothing is silently wrong, and nothing is pruned:
feature selection stays a separate, user-controlled step.
"""

from __future__ import annotations

from geeflow.specs import KNOWN_INDICES


def _ndvi(img):
    return img.normalizedDifference(["NIR", "Red"]).rename("NDVI")


def _savi(img):
    # L = 0.5
    return img.expression(
        "((NIR - RED) / (NIR + RED + 0.5)) * 1.5",
        {"NIR": img.select("NIR"), "RED": img.select("Red")},
    ).rename("SAVI")


def _evi(img):
    return img.expression(
        "2.5 * (NIR - RED) / (NIR + 6.0 * RED - 7.5 * BLUE + 1.0)",
        {"NIR": img.select("NIR"), "RED": img.select("Red"), "BLUE": img.select("Blue")},
    ).rename("EVI")


def _ndmi(img):
    return img.normalizedDifference(["NIR", "SWIR1"]).rename("NDMI")


def _nbr(img):
    return img.normalizedDifference(["NIR", "SWIR2"]).rename("NBR")


def _blue_green_nir(img):
    return img.expression(
        "(BLUE + GREEN) / NIR",
        {"BLUE": img.select("Blue"), "GREEN": img.select("Green"), "NIR": img.select("NIR")},
    ).rename("BlueGreenNIR")


def _green_red(img):
    return img.expression(
        "GREEN / RED",
        {"GREEN": img.select("Green"), "RED": img.select("Red")},
    ).rename("GreenRed")


def _ndre(img):
    return img.normalizedDifference(["NIR", "RedEdge1"]).rename("NDRE")


def _cire(img):
    return img.expression(
        "NIR / RE1 - 1",
        {"NIR": img.select("NIR"), "RE1": img.select("RedEdge1")},
    ).rename("CIre")


def _ndwi(img):
    return img.normalizedDifference(["Green", "NIR"]).rename("NDWI")


def _ndbi(img):
    return img.normalizedDifference(["SWIR1", "NIR"]).rename("NDBI")


BUILDERS = {
    "NDVI": _ndvi,
    "SAVI": _savi,
    "EVI": _evi,
    "NDMI": _ndmi,
    "NBR": _nbr,
    "BlueGreenNIR": _blue_green_nir,
    "GreenRed": _green_red,
    "NDRE": _ndre,
    "CIre": _cire,
    "NDWI": _ndwi,
    "NDBI": _ndbi,
}


def computable_indices(index_names: list[str], available_bands: list[str]) -> list[str]:
    """The subset of requested indices whose required bands are all present."""
    bands = set(available_bands)
    return [n for n in index_names if set(KNOWN_INDICES[n]) <= bands]


def add_indices(image, index_names: list[str], available_bands: list[str]):
    """Add every computable requested index as a band.

    Returns (image_with_indices, names_of_added_indices).
    """
    names = computable_indices(index_names, available_bands)
    if not names:
        return image, []
    return image.addBands([BUILDERS[n](image) for n in names]), names
