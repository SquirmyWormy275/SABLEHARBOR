"""Portable bookmarked spatial addendum; prior atlas publication stays intact."""

import fitz


def compile_pdf(root, maps):
    doc = fitz.open()
    toc = []
    # Each independently saved sheet is a page; bookmarks carry complete stable identities.
    for m in maps:
        page_number = len(doc) + 1
        with fitz.open(root / m["artifacts"]["pdf"]["path"]) as source:
            doc.insert_pdf(source)
        toc.append([1, m.get("map_id", m["id"]) + " · " + m["title"], page_number])
    doc.set_toc(toc)
    doc.set_metadata(
        {
            "title": "Sable Harbor Spatial Architectural Addendum v1.0.0",
            "author": "Sable Harbor",
            "creationDate": "D:20260911000000Z",
            "modDate": "D:20260911000000Z",
        }
    )
    path = root / "geospatial/maps/SABLE_HARBOR_Spatial_Addendum_v1.0.0.pdf"
    doc.save(path, garbage=4, deflate=True, no_new_id=True)
    return path
