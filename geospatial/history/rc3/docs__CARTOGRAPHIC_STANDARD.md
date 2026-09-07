# Cartographic standard

Map sheets are generated directly from the GeoPackage. Restrained navy typography, teal study boundaries, burgundy disputed geography, muted roads/rail and blue hydrography separate the important assertions. No generated raster imagery, invented relief or reconstructed logo is used as a map source.

All sheets have an ID, title, status, version, world-state date, source-commit prefix, projection, attribution and precision note. Regional maps use NAD83 / UTM 10N for Sacramento, 17N for Pennsylvania/West Virginia and 13N for Wyoming; continental context uses EPSG:5070. Scale bars use projected metric coordinates. Regional north arrows explicitly show grid north; they are not magnetic bearings.

Hatching marks an analyst search envelope, not a property boundary. Burgundy marks a conflict. Municipal open-circle labels locate reference places; they are not facility pins. Real rail remains subdued context. Empty fictional rail layers are not drawn. The Red Wash map's distance is a WGS84 geodesic comparison, not track mileage.

Source images are evidence, not the master database. The recovered Red Wash conceptual maps retain their original bytes and are not resampled into a purported survey. The new maps summarize the conflict with independently located source claims.

PDF, SVG, PNG and JSON sidecars are exported together. A JSON sidecar records the master-package hash, layer set, map status, build timestamp and hashes of each output. A visual QA record refers to the exact reviewed files. An engineering map or site plan is withheld when the defining geometry is not yet credible; a polished placeholder cannot satisfy that requirement.
