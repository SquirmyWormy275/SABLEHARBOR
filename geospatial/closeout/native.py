"""Native QGIS qualification and relocated-project verification for a built package."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsVectorLayer,
    QgsRelation,
    QgsMapSettings,
    QgsMapRendererParallelJob,
    QgsCoordinateReferenceSystem,
    Qgis,
)
from qgis.PyQt.QtCore import QSize


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(package):
    gpkg = package / "geospatial/master/sable_harbor_master_v0.1.gpkg"
    project_path = package / "geospatial/qgis/sable_harbor_master.qgz"
    with sqlite3.connect(gpkg) as db:
        expected = {
            name: (kind, db.execute('SELECT COUNT(*) FROM "' + name + '"').fetchone()[0])
            for name, kind in db.execute("SELECT table_name,data_type FROM gpkg_contents")
        }
    app = QgsApplication([], False)
    app.initQgis()
    project = QgsProject.instance()
    if not project.read(str(project_path)):
        raise ValueError("Cannot open the packaged QGIS project")
    group = project.layerTreeRoot().addGroup("Evidence and source registers")
    existing = {layer.name(): layer for layer in project.mapLayers().values()}
    for name, (kind, _) in expected.items():
        if kind == "attributes" and name not in existing:
            layer = QgsVectorLayer(str(gpkg) + "|layername=" + name, name, "ogr")
            if not layer.isValid():
                raise ValueError("Cannot read attribute table: " + name)
            project.addMapLayer(layer, False)
            group.addLayer(layer)
            existing[name] = layer
    relation = QgsRelation()
    relation.setId("review_site_to_object")
    relation.setName("Site evidence to canonical object")
    relation.setReferencedLayer(existing["object_registry"].id())
    relation.setReferencingLayer(existing["review_site_evidence"].id())
    relation.addFieldPair("object_id", "object_id")
    if not relation.isValid():
        raise ValueError("Site-object relation is invalid")
    project.relationManager().addRelation(relation)
    if not project.write(str(project_path)):
        raise ValueError("Cannot save the enriched portable project")
    settings = QgsMapSettings()
    settings.setLayers(
        [layer for layer in project.layerTreeRoot().layerOrder() if layer.isSpatial()]
    )
    settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    settings.setOutputSize(QSize(1600, 1000))
    settings.setExtent(settings.fullExtent())
    job = QgsMapRendererParallelJob(settings)
    job.start()
    job.waitForFinished()
    if not job.renderedImage().save(str(package / "MAP_PREVIEW.png")):
        raise ValueError("Native map rendering failed")
    checks = []
    with tempfile.TemporaryDirectory(prefix="sable-geo-relocation-") as temp:
        moved = Path(temp)
        (moved / "geospatial/master").mkdir(parents=True)
        (moved / "geospatial/qgis").mkdir(parents=True)
        shutil.copy2(gpkg, moved / "geospatial/master" / gpkg.name)
        shutil.copy2(project_path, moved / "geospatial/qgis" / project_path.name)
        for label, source in (
            ("original", project_path),
            ("relocated", moved / "geospatial/qgis" / project_path.name),
        ):
            project.clear()
            if not project.read(str(source)):
                raise ValueError("Project relocation failed")
            layers = {layer.name(): layer for layer in project.mapLayers().values()}
            if set(layers) != set(expected):
                raise ValueError("Project omits a registered layer/table")
            for name, (kind, count) in expected.items():
                layer = layers[name]
                actual_database = Path(layer.source().split("|", 1)[0]).resolve()
                expected_database = source.parent.parent / "master" / gpkg.name
                passed = (
                    layer.isValid()
                    and layer.featureCount() == count
                    and actual_database == expected_database.resolve()
                )
                if kind == "features":
                    passed = passed and layer.crs().authid() == "EPSG:4326"
                checks.append(
                    {
                        "location": label,
                        "name": name,
                        "kind": kind,
                        "expected_count": count,
                        "observed_count": layer.featureCount(),
                        "database_is_local": actual_database == expected_database.resolve(),
                        "passed": passed,
                    }
                )
                if not passed:
                    raise ValueError("Native layer validation failed: " + name)
            if not project.relationManager().relations()["review_site_to_object"].isValid():
                raise ValueError("Relocated site-object relation failed")
    report = {
        "passed": True,
        "qgis_version": Qgis.QGIS_VERSION,
        "checks": checks,
        "gpkg_sha256": sha(gpkg),
        "project_sha256": sha(project_path),
        "source_revision": json.loads((package / "BUILD.json").read_text())["source_revision"],
        "map_preview_sha256": sha(package / "MAP_PREVIEW.png"),
    }
    (package / "NATIVE_QGIS.json").write_text(json.dumps(report, indent=2) + "\n")
    project.clear()
    app.exitQgis()
    print(json.dumps({"native_checks": len(checks), "passed": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    qualify(args.package.resolve())
