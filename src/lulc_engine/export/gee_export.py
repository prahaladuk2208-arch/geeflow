"""Export classified images to Google Drive or an Earth Engine asset."""

from __future__ import annotations

import ee

from lulc_engine.config.schema import LulcConfig


def export_classification(classified, aoi, cfg: LulcConfig, year: int, model_name: str, log=print):
    """Start the export task for a classified image. Returns the ee task."""
    exp = cfg.export
    scale = exp.scale_m or cfg.scale_for_year(year)
    description = f"{exp.prefix}_{year}_{model_name}"
    image = classified.toUint8()

    if exp.target == "drive":
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=description,
            folder=exp.folder,
            fileNamePrefix=description,
            region=aoi,
            scale=scale,
            maxPixels=exp.max_pixels,
            crs=exp.crs,
        )
    else:  # asset
        task = ee.batch.Export.image.toAsset(
            image=image,
            description=description,
            assetId=f"{exp.asset_root}/{description}",
            region=aoi,
            scale=scale,
            maxPixels=exp.max_pixels,
        )

    task.start()
    log(f"\nExport task started: {description}")
    log("Track progress at: https://code.earthengine.google.com/tasks")
    if exp.target == "drive":
        log(f"Output will appear in Google Drive folder: {exp.folder}/")
    return task
