"""GLCM texture metrics."""

from __future__ import annotations

from lulc_engine.config.schema import TextureConfig

# glcmTexture() output band suffix per metric
_GLCM_SUFFIX = {
    "entropy": "ent",
    "contrast": "contrast",
    "variance": "var",
    "correlation": "corr",
}


def add_texture(image, cfg: TextureConfig, available_bands: list[str]):
    """Add GLCM texture bands computed from cfg.band.

    Reflectance is scaled to integers (x10000) because glcmTexture needs an int image.
    Returns (image_with_texture, names_of_added_bands).
    """
    if not cfg.enabled or cfg.band not in available_bands:
        return image, []

    size = (cfg.window - 1) // 2  # glcmTexture size=1 -> 3x3 window
    scaled = image.select(cfg.band).multiply(10000).toInt()
    glcm = scaled.glcmTexture(size=size)

    added = []
    names = []
    for metric in cfg.metrics:
        src = f"{cfg.band}_{_GLCM_SUFFIX[metric]}"
        name = f"GLCM_{metric}"
        added.append(glcm.select(src).rename(name))
        names.append(name)
    return image.addBands(added), names
