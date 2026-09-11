"""Cross-generator regression: a source fixture cannot be silently ignored."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from enterprise.runtime import model, report, planning
from enterprise.services import model as services
from geospatial.scripts.sync_runtime import synchronize
from tools.documents import build_institutional_catalog as catalog


def test_runtime_fixture_changes_services_finance_geography_contract_and_catalog():
    original = model.load()
    changed = copy.deepcopy(original)
    changed["sites"]["sites"][1]["name"] = "SYNTHETIC MUTATION Boise display record"
    changed["sites"]["sites"][1]["published_planning_price_usd_per_kw_month"] = 350
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "source"
        source.mkdir()
        for name in services.FILES:
            path = model.ROOT / "enterprise/services/source" / f"{name}.json"
            (source / path.name).write_bytes(path.read_bytes())
        for key, relative in model.FILES.items():
            (source / Path(relative).name).write_text(json.dumps(changed[key], indent=2) + "\n")
        output = root / "service-output"
        services.build(services.load(source), output)
        exported = json.loads((output / "runtime.json").read_text())
        assert exported["contract_covers"][1]["site_name"] == changed["sites"]["sites"][1]["name"]
        baseline = next(
            r
            for r in planning.finance(original)["annual"]
            if r["scenario"] == "base" and r["year"] == 2027
        )
        mutated = next(
            r
            for r in exported["finance"]["annual"]
            if r["scenario"] == "base" and r["year"] == 2027
        )
        assert baseline["operating_cash_request"] != mutated["operating_cash_request"]
        geography = json.loads((model.ROOT / "geospatial/sources/catalog.json").read_text())
        synced, _ = synchronize(geography, changed)
        site = next(r for r in synced["objects"] if r["object_id"] == "SH-SITE-0029")
        assert site["canonical_name"] == changed["sites"]["sites"][1]["name"]
        # Execute the real catalog builder on a deliberately isolated synthetic publication fixture.
        manuscript = root / "results.md"
        publication = root / "fixture.pdf"
        manifest = root / "manifest.json"
        publication.write_bytes(b"SYNTHETIC CATALOG HASH FIXTURE; NOT A RELEASE PDF")
        identities = []
        for data in (original, changed):
            manuscript.write_text(report.render(data))
            manifest.write_text(
                json.dumps(
                    {
                        "generated_for_version": "2026-09-11",
                        "artifacts": [
                            {
                                "source": "results.md",
                                "publication": "fixture.pdf",
                                "source_sha256": hashlib.sha256(
                                    manuscript.read_bytes()
                                ).hexdigest(),
                                "sha256": hashlib.sha256(publication.read_bytes()).hexdigest(),
                            }
                        ],
                    }
                )
            )
            with patch.multiple(
                catalog,
                ROOT=root,
                MANIFEST=manifest,
                OUT_JSON=root / "catalog.json",
                OUT_DB=root / "catalog.sqlite3",
            ):
                catalog.main()
            item = json.loads((root / "catalog.json").read_text())["objects"][0]
            identities.append(item["source_sha256"])
        assert identities[0] != identities[1]
        assert "synthetic mutation boise display record" in item["search_text"]
