# Rights and source attribution

The repository's [LICENSE.md](../LICENSE.md) governs original Sable Harbor text, source artwork, fictional geography and authored deliverables. This package does not grant additional rights in that material. Public repository visibility does not change its license.

| Material | Rights / attribution | Source statement |
|---|---|---|
| Census TIGER reference states, counties, places | U.S. Census Bureau; public-domain geographic data. No agency endorsement. | [Census statement identifying TIGER as public domain](https://www.census.gov/newsroom/archives/2014-pr/cb14-208.html) |
| USGS transportation and hydrography snapshots | USGS The National Map, with Census Bureau / U.S. Forest Service transportation attribution; federal reference data | [USGS copyrights and credits](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits), [USGS statement on public-domain TIGER roads](https://www.usgs.gov/news/national-news-release/new-heartland-maps-new-year) |
| FRA / BTS North American Rail Network extract | Federal Railroad Administration / Bureau of Transportation Statistics; federal reference data | [FRA GIS data page](https://railroads.dot.gov/rail-network-development/maps-and-data/maps-geographic-information-system/maps-geographic) |
| Two NAIP screening images | USDA NAIP via USGS. Public-domain imagery; source catalog and exported extents retained. | [USGS NAIP service statement](https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer) |
| Municipal, university, developer and company web research | Linked and briefly summarized. No blanket reuse license is inferred and no third-party website images are copied. | Individual links in `docs/SITE_SELECTION_EVIDENCE.md` |
| Attached NAILEX authority research | User-provided research inspected for scope; original report not redistributed in this geospatial package. | Hash and inspection scope in `sources/catalog.json` |

`sources/reference_manifest.json` supplies the exact endpoint, query, access date, file hash, response hashes, attribution and license URL for each GIS extract. `sources/site_reference/manifest.json` supplies imagery provenance. A public-domain source does not establish title, access rights, operating authority or fictional corporate ownership.

Software is installed from its upstream distributions under its respective licenses. No bundled third-party software or fonts are redistributed as separate assets. PDF fonts are embedded by Matplotlib from its installed DejaVu font distribution.
