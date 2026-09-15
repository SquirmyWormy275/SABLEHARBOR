"""Portable human-readable research dockets with embedded evidence and search."""

import html
import json

STYLE = """body{margin:0;background:#f5f2eb;color:#203b36;font:17px/1.6 system-ui}header{background:#203b36;color:#f5f2eb;padding:36px max(24px,calc((100vw - 1120px)/2));border-bottom:5px solid #a2602d}h1{font-size:clamp(30px,4vw,48px);line-height:1.15}main{max-width:1120px;margin:auto;padding:28px}a{color:inherit;text-underline-offset:3px}input,select,button{font:inherit;padding:10px;border:1px solid #91a096;background:#fffef9;color:#203b36;max-width:100%;box-sizing:border-box}article{background:#fffef9;padding:24px;border:1px solid #d7dbd1;margin:20px 0;overflow-wrap:anywhere}h2{font-size:24px;margin-top:0}small{color:#65736b}header small{color:#d3dfd2}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.5 ui-monospace,monospace;background:#f0f2ec;padding:16px}details{margin-top:14px}summary{cursor:pointer;font-weight:600}article[hidden]{display:none}.controls{display:flex;flex-wrap:wrap;gap:12px;align-items:end}.controls label{display:flex;flex-direction:column;gap:5px}.badge{display:inline-block;border-left:4px solid #a2602d;padding-left:12px;font-size:15px}nav{margin:20px 0}button:disabled{opacity:.45}@media(max-width:600px){main{padding:16px}article{padding:18px}input{width:100%}}"""


def page(title, intro, body, script=""):
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sable Harbor · '
        + html.escape(title)
        + "</title><style>"
        + STYLE
        + "</style><header><small>SABLE HARBOR / GEOGRAPHIC RESEARCH</small><h1>"
        + html.escape(title)
        + "</h1><p>"
        + html.escape(intro)
        + '</p></header><main><nav><a href="maps/index.html">Historical and site atlas</a> · <a href="site-docket.html">Site evidence</a> · <a href="source-review.html">Source review</a> · <a href="../chronology/history.html">Interactive chronology</a></nav>'
        + body
        + "</main>"
        + script
        + "</html>"
    )


def write(output, docket, reviewed, summary):
    cards = []
    observations = {r["observation_id"]: r for r in docket["observations"]}
    for r in docket["records"]:
        source = r["primary_source"]
        parts = []
        for oid in r["observations"]:
            o = observations[oid]
            s = o["source"]
            parts.append(
                "<details><summary>"
                + html.escape(o["kind"].replace("_", " ").capitalize())
                + "</summary><p>"
                + html.escape(o["meaning"])
                + "</p><pre>"
                + html.escape(s["text"])
                + "</pre><small>"
                + html.escape(s["path"] + " · " + s["locator"] + " · " + s["revision"])
                + "</small></details>"
            )
        bounds = r["occupancy_bounds"]
        temporal = (
            "Year-bounded occupancy is approved; exact entry and exit days remain unknown."
            if bounds
            else r["temporal_meaning"]
        )
        cards.append(
            '<article data-title="'
            + html.escape(r["name"] + " " + r["object_id"], quote=True)
            + '"><small>'
            + r["object_id"]
            + "</small><h2>"
            + html.escape(r["name"])
            + '</h2><p class="badge">'
            + html.escape(r["disposition"].replace("_", " ").capitalize())
            + "</p><p>"
            + html.escape(temporal)
            + "</p><p><strong>Controlling decision and precision:</strong> "
            + html.escape(r["required_action"])
            + "</p>"
            + "".join(parts)
            + "<details><summary>Primary archived source and current spatial evidence</summary><pre>"
            + html.escape(
                json.dumps(
                    dict(
                        primary_source=source,
                        current_decision=r.get("current_decision_evidence"),
                        spatial_evidence=r["spatial_evidence"],
                        approved_occupancy_bounds=bounds,
                    ),
                    indent=2,
                )
            )
            + "</pre></details></article>"
        )
    script = """<script>const input=document.querySelector('#filter'),cards=[...document.querySelectorAll('article')];function apply(){let count=0;for(const c of cards){c.hidden=!c.dataset.title.toLowerCase().includes(input.value.toLowerCase());if(!c.hidden)count++}document.querySelector('#count').textContent=count+' site and component records';}input.addEventListener('input',apply);apply();</script>"""
    body = (
        '<p>Every site retains a stable identity, source evidence and a specific next action. Proposed offices, shared functions, operating hosts and component records have different requirements.</p><label for="filter">Find a site or stable ID</label><br><input id="filter" type="search" placeholder="Bedford, SH-SITE-0011…"><p id="count" aria-live="polite"></p>'
        + "".join(cards)
    )
    (output / "site-docket.html").write_text(
        page(
            "Site evidence & decisions",
            "34 sites and components. Accepted facts stay separate from design alternatives and unresolved occupancy.",
            body,
            script,
        )
    )
    data = json.dumps(reviewed, ensure_ascii=False).replace("</", "<\\/")
    script = (
        """<script id="source-data" type="application/json">"""
        + data
        + """</script><script>
const rows=JSON.parse(document.querySelector('#source-data').textContent),query=document.querySelector('#query'),scope=document.querySelector('#scope'),results=document.querySelector('#results');let pageIndex=0;const size=40;for(const kind of [...new Set(rows.map(r=>r.disposition))].sort()){const o=document.createElement('option');o.value=kind;o.textContent=kind.toLowerCase().replaceAll('_',' ');scope.append(o)}
function render(){const needle=query.value.toLowerCase(),matched=rows.filter(r=>(!scope.value||r.disposition===scope.value)&&[r.source_path,r.source_locator,r.exact_source_wording,r.occurrence_id].join(' ').toLowerCase().includes(needle));pageIndex=Math.min(pageIndex,Math.max(0,Math.ceil(matched.length/size)-1));results.replaceChildren();for(const r of matched.slice(pageIndex*size,(pageIndex+1)*size)){const card=document.createElement('article'),heading=document.createElement('h2'),small=document.createElement('small'),kind=document.createElement('p'),quote=document.createElement('pre'),limit=document.createElement('p'),detail=document.createElement('details'),summary=document.createElement('summary'),context=document.createElement('pre');heading.textContent=r.source_path;small.textContent=r.occurrence_id+' · '+r.source_locator;kind.textContent=r.disposition.toLowerCase().replaceAll('_',' ');kind.className='badge';quote.textContent=r.exact_source_wording;limit.textContent=r.limit;summary.textContent='Full retained record and provenance';context.textContent=JSON.stringify(r,null,2);detail.append(summary,context);card.append(heading,small,kind,quote,limit,detail);results.append(card)}document.querySelector('#count').textContent=matched.length+' matching records · page '+(pageIndex+1)+' of '+Math.max(1,Math.ceil(matched.length/size));document.querySelector('#previous').disabled=pageIndex===0;document.querySelector('#next').disabled=(pageIndex+1)*size>=matched.length;}
for(const e of [query,scope])e.addEventListener('input',()=>{pageIndex=0;render()});document.querySelector('#previous').onclick=()=>{pageIndex--;render()};document.querySelector('#next').onclick=()=>{pageIndex++;render()};render();</script>"""
    )
    body = f"""<p>{summary["reviewed_carriers"]:,} exact discovery records across {summary["source_files"]} archived files are classified here. {summary["remaining_carriers"]:,} records remain outside the five completed batches. This is carrier review, not a claim that every narrative, publication or subsequent source delta has been semantically resolved.</p><p><a href="SOURCE_REVIEW.csv.gz">Complete review CSV</a> · <a href="REMAINING_OCCURRENCES.csv.gz">Remaining records CSV</a> · <a href="RASTER_REVIEW.json">Visual dispositions</a> · <a href="ocr/RASTER_INVENTORY.json">PDF and archive-image coverage</a></p><div class="controls"><label>Search source, text or ID<input id="query" type="search"></label><label>Disposition<select id="scope"><option value="">All reviewed records</option></select></label></div><p id="count" aria-live="polite"></p><button id="previous">Previous page</button> <button id="next">Next page</button><section id="results"></section>"""
    (output / "source-review.html").write_text(
        page(
            "Source review",
            "Exact source carriers, preserved context, explicit interpretations.",
            body,
            script,
        )
    )
