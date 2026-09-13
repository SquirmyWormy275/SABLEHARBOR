"""Retrieve public USGS imagery and elevation for reproducible site screening."""

import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "geospatial/finalization/reference"
SERVICES = {
    "imagery": "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer",
    "elevation": "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer",
}


def get(url):
    with urllib.request.urlopen(url, timeout=90) as response:
        return response.read()


def retrieve(task):
    feature, kind = task
    points = feature["geometry"]["coordinates"][0]
    xs, ys = zip(*points)
    bounds = [min(xs) - 0.0015, min(ys) - 0.0012, max(xs) + 0.0015, max(ys) + 0.0012]
    params = dict(
        bbox=",".join(map(str, bounds)),
        bboxSR=4326,
        imageSR=4326,
        size="800,800" if kind == "imagery" else "256,256",
        format="png" if kind == "imagery" else "tiff",
        f="json",
    )
    if kind == "elevation":
        params.update(pixelType="F32", interpolation="RSP_BilinearInterpolation")
    url = SERVICES[kind] + "/exportImage?" + urllib.parse.urlencode(params)
    raw = get(url)
    meta = json.loads(raw)
    if "href" not in meta:
        raise ValueError(meta)
    data = get(meta["href"])
    stem = feature["properties"]["option_id"] + "-" + kind
    filename = stem + (".png" if kind == "imagery" else ".tif")
    (OUT / filename).write_bytes(data)
    (OUT / (stem + ".json")).write_bytes(raw)
    return dict(
        option_id=feature["properties"]["option_id"],
        kind=kind,
        request_url=url,
        metadata_file=stem + ".json",
        metadata_sha256=hashlib.sha256(raw).hexdigest(),
        file=filename,
        sha256=hashlib.sha256(data).hexdigest(),
        extent=meta["extent"],
        accessed_date="2026-09-13",
        authority="USDA NAIP / USGS The National Map"
        if kind == "imagery"
        else "USGS 3DEP",
        license="US federal public-domain imagery/elevation; catalog attribution retained separately",
        use="Fictional planning compatibility screen; no vacancy, rights or geotechnical certification",
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    features = json.loads(
        (ROOT / "geospatial/completion/SITE_OPTIONS.geojson").read_text()
    )["features"]
    tasks = [(f, k) for f in features for k in SERVICES]
    records = []
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pending = {pool.submit(retrieve, t): t for t in tasks}
        for future in concurrent.futures.as_completed(pending):
            f, k = pending[future]
            try:
                records.append(future.result())
                print(f["properties"]["option_id"], k, "fetched", flush=True)
            except Exception as error:
                failures.append(
                    dict(
                        option_id=f["properties"]["option_id"], kind=k, error=str(error)
                    )
                )
                print(failures[-1], flush=True)
    (OUT / "MANIFEST.json").write_text(
        json.dumps(
            dict(
                records=sorted(records, key=lambda x: (x["option_id"], x["kind"])),
                failures=failures,
            ),
            indent=2,
        )
        + "\n"
    )
    if failures:
        raise SystemExit(
            "Some reference requests failed; inspect manifest before retrying"
        )


if __name__ == "__main__":
    main()
