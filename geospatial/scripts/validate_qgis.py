#!/usr/bin/env python3
"""Native QGIS read, independent feature-count and relocated-project check."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from qgis.core import QgsApplication, QgsProject, Qgis

BASE = Path(__file__).resolve().parents[1]
gpkg = BASE / "master/sable_harbor_master_v0.1.gpkg"
with sqlite3.connect(gpkg) as db:
    names = [r[0] for r in db.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'")]
    expected = {n: db.execute('SELECT COUNT(*) FROM "' + n + '"').fetchone()[0] for n in names}

app = QgsApplication([], False)
app.initQgis()
project = QgsProject.instance()
checks = []
with tempfile.TemporaryDirectory(prefix="sh-qgis-relocation-") as temp:
    moved = Path(temp)
    (moved / "master").mkdir()
    (moved / "qgis").mkdir()
    shutil.copy2(gpkg, moved / "master" / gpkg.name)
    source_project = BASE / "qgis/sable_harbor_master.qgz"
    shutil.copy2(source_project, moved / "qgis" / source_project.name)
    for name, path in [("original", source_project), ("relocated", moved / "qgis" / source_project.name)]:
        read = project.read(str(path))
        layers = []
        for layer in sorted(project.mapLayers().values(), key=lambda x: x.name()):
            count = layer.featureCount() if layer.isValid() else None
            layers.append(dict(name=layer.name(), valid=layer.isValid(), feature_count=count,
                               expected_count=expected.get(layer.name()), crs=layer.crs().authid(),
                               renderer=layer.renderer().type() if layer.renderer() else None))
        passed = read and len(layers) == len(expected) and all(
            l["valid"] and l["feature_count"] == l["expected_count"] and l["crs"] == "EPSG:4326" and (l["renderer"] or l["feature_count"] == 0) for l in layers)
        checks.append(dict(check=name, project_read=read, layer_count=len(layers), layers=layers, status="PASS" if passed else "FAIL"))
        project.clear()

result = dict(qgis_version=Qgis.QGIS_VERSION, validation_commit=os.environ.get("GITHUB_SHA"),
              package_sha256=hashlib.sha256(gpkg.read_bytes()).hexdigest(),
              project_sha256=hashlib.sha256(source_project.read_bytes()).hexdigest(),
              checks=checks, status="PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL")
(BASE / "reports/QGIS_VALIDATION.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
app.exitQgis()
raise SystemExit(0 if result["status"] == "PASS" else 1)
