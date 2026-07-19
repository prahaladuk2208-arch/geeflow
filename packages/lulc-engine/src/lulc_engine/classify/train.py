"""Final training + full-image classification, natively in Earth Engine.

CV/model comparison happens client-side in scikit-learn on sampled pixels; the winning
model is then retrained on ALL training pixels with the equivalent GEE classifier and
applied to the full feature stack server-side.
"""

from __future__ import annotations

import ee

from lulc_engine.config.schema import LulcConfig


def make_gee_classifier(name: str, cfg: LulcConfig):
    c = cfg.classifier
    if name == "RF":
        return ee.Classifier.smileRandomForest(
            numberOfTrees=c.rf.trees,
            bagFraction=c.rf.bag_fraction,
            seed=c.rf.seed,
        )
    if name == "GBT":
        return ee.Classifier.smileGradientTreeBoost(
            numberOfTrees=c.gbt.trees,
            seed=c.gbt.seed,
        )
    if name == "SVM":
        return ee.Classifier.libsvm(
            kernelType=c.svm.kernel,
            cost=c.svm.cost,
            gamma=c.svm.gamma,
        )
    raise ValueError(f"unknown classifier {name!r}")


def train_and_classify(
    feature_stack,
    training_fc,
    feature_cols: list[str],
    best_name: str,
    cfg: LulcConfig,
    year: int,
    log=print,
):
    """Train the winning classifier on all pixels in GEE and classify the stack."""
    stack_sel = feature_stack.select(feature_cols)

    training_data = stack_sel.sampleRegions(
        collection=training_fc,
        properties=[cfg.training.class_property],
        scale=cfg.scale_for_year(year),
    )

    classifier = make_gee_classifier(best_name, cfg).train(
        features=training_data,
        classProperty=cfg.training.class_property,
        inputProperties=feature_cols,
    )

    log(f"Classifying full image with {best_name} ({len(feature_cols)} features)...")
    return stack_sel.classify(classifier)
