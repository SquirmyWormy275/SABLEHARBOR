# R02 non-Sacramento visual review — first pass

**Status: corrections required; not final acceptance.** All 42 non-Sacramento sheets in the first 58-sheet R02 manifest were manually inspected as individual PDF renders at 1600 pixels wide. Seven retained contact sheets support comparative review. The renderer has since changed; this report preserves the first-pass findings rather than certifying later outputs. The companion JSON records all 126 manifest artifact hashes and each inspected PDF raster hash.

| ID | Finding | Affected surfaces / correction |
|---|---|---|
| R02-NS-01 | West dimension labels extend outside the page. Metric conversion creates misleading four-decimal foot labels. | ARU023/025/032/042; WIL022/024/025/027; CRD022/024/026/028. Move/rotate dimensions inside margins and round at concept precision. |
| R02-NS-02 | Industrial circulation/support strips lack labels and internal openings, while narrative claims coordinated room access. | All six industrial floors; label explicit support/circulation regions and distinguish open operational zone boundaries from enclosed partitions. Show access consistently without fabricating installed process engineering. |
| R02-NS-03 | Site dependency panels print literal “None” despite unresolved source engineering and occupancy. | ARU021/027/030/036/040. Render source dependencies or explicit unresolved design statement. |
| R02-NS-04 | RWM021's 100-foot scale bar is too short for readable 0/50/100 labels. | Choose an interval appropriate to the 1000-metre envelope. |
| R02-NS-05 | Door arcs overlap south-row room titles. | Most research floors; notably six WIL025 guest rooms and WIL027/CRD receipt, analytical, fabrication and storage rooms. Place titles below the swing or clear of it. |
| R02-NS-06 | Building program prose and site schedule names truncate without continuation. | WIL021 ends “Experiment readin”; CRD020 schedule truncates four long names. Wrap complete words and preserve all functions. |
| R02-NS-07 | Exit/stair core labels identify access but do not show corridor/exterior thresholds. | Research floors. Clarify schematic openings while retaining existing fixed core geometry and engineering caveats. |

The source comparison preserves Taylor 210,000 sf and Rawlins 75,000 sf warehouses as broad storage/handling envelopes, not invented racks or plant. Red Wash technical geometry remains unresolved; no underground workings, process equipment or rejected rail spur appears. Truck-served Rawlins remains without invented track. Fort retains three sheds and the outdoor Museum; Bedford remains a separate Fairmont model with four buildings. Site/building/floor status notes distinguish concepts from actual occupancy. The six Fort guest rooms remain single rooms opening independently to a common corridor; their door/title drawing collision is a presentation defect, not a source count change.

An initial standalone SVG raster comparison used the default system font configuration rather than the renderer's pinned repository fonts. Its pixel differences are not treated as a rendering defect. Final QA must rerun under the committed font configuration, inspect revised PNG/PDF surfaces, verify actual current bytes against manifest hashes, and bind the findings to the final manifest. No final pass is asserted by this report.
