"""Export images to Google Drive or an Earth Engine asset."""

from __future__ import annotations

import ee


def export_image(
    image,
    region,
    description: str,
    target: str = "drive",
    folder: str = "geeflow_outputs",
    asset_root: str | None = None,
    scale: int = 30,
    crs: str = "EPSG:4326",
    max_pixels: float = 1e10,
    to_uint8: bool = False,
    log=print,
):
    """Start an export task. Returns the ee task.

    target: "drive" exports to the given Drive folder; "asset" exports to
    {asset_root}/{description} and requires asset_root.
    """
    if to_uint8:
        image = image.toUint8()

    if target == "drive":
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=description,
            folder=folder,
            fileNamePrefix=description,
            region=region,
            scale=scale,
            maxPixels=max_pixels,
            crs=crs,
        )
    elif target == "asset":
        if not asset_root:
            raise ValueError("asset_root is required for target='asset'")
        task = ee.batch.Export.image.toAsset(
            image=image,
            description=description,
            assetId=f"{asset_root}/{description}",
            region=region,
            scale=scale,
            maxPixels=max_pixels,
        )
    else:
        raise ValueError(f"unknown export target {target!r}")

    task.start()
    log(f"\nExport task started: {description}")
    log("Track progress at: https://code.earthengine.google.com/tasks")
    if target == "drive":
        log(f"Output will appear in Google Drive folder: {folder}/")
    return task
