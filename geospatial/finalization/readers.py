"""Offline, paginated final-review readers with exact source context."""

import json
from geospatial.completion.readers import page


def write(directory, name, title, intro, rows):
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    script = (
        """<script id="source-data" type="application/json">"""
        + data
        + """</script><script>
const rows=JSON.parse(document.querySelector('#source-data').textContent),query=document.querySelector('#query'),scope=document.querySelector('#scope'),results=document.querySelector('#results');let pageIndex=0;const size=40;for(const kind of [...new Set(rows.map(r=>r.disposition))].sort()){const o=document.createElement('option');o.value=kind;o.textContent=kind.toLowerCase().replaceAll('_',' ');scope.append(o)}
function render(){const needle=query.value.toLowerCase(),matched=rows.filter(r=>(!scope.value||r.disposition===scope.value)&&[r.source_path,r.source_locator,r.exact_source_wording,r.occurrence_id].join(' ').toLowerCase().includes(needle));pageIndex=Math.min(pageIndex,Math.max(0,Math.ceil(matched.length/size)-1));results.replaceChildren();for(const r of matched.slice(pageIndex*size,(pageIndex+1)*size)){const card=document.createElement('article'),heading=document.createElement('h2'),small=document.createElement('small'),kind=document.createElement('p'),quote=document.createElement('pre'),limit=document.createElement('p'),detail=document.createElement('details'),summary=document.createElement('summary'),context=document.createElement('pre');heading.textContent=r.source_path;small.textContent=r.occurrence_id+' · '+r.source_locator;kind.textContent=r.disposition.toLowerCase().replaceAll('_',' ');kind.className='badge';quote.textContent=r.exact_source_wording;limit.textContent=r.limit;summary.textContent='Full retained record and provenance';context.textContent=JSON.stringify(r,null,2);detail.append(summary,context);card.append(heading,small,kind,quote,limit,detail);results.append(card)}document.querySelector('#count').textContent=matched.length+' matching records · page '+(pageIndex+1)+' of '+Math.max(1,Math.ceil(matched.length/size));document.querySelector('#previous').disabled=pageIndex===0;document.querySelector('#next').disabled=(pageIndex+1)*size>=matched.length;}
for(const e of [query,scope])e.addEventListener('input',()=>{pageIndex=0;render()});document.querySelector('#previous').onclick=()=>{pageIndex--;render()};document.querySelector('#next').onclick=()=>{pageIndex++;render()};render();</script>"""
    )
    body = '<nav><a href="index.html">Current decisions</a> · <a href="source-review.html">Final carrier review</a> · <a href="source-ledger.html">Source ledger</a></nav><div class="controls"><label>Search source, text or ID<input id="query" type="search"></label><label>Disposition<select id="scope"><option value="">All records</option></select></label></div><p id="count" aria-live="polite"></p><button id="previous">Previous page</button> <button id="next">Next page</button><section id="results"></section>'
    rendered = page(title, intro, body, script).replace(
        "</style>",
        ".controls label{min-width:0;max-width:100%}.controls select{width:100%}</style>",
    )
    start = rendered.index("<nav>")
    end = rendered.index("</nav>", start) + len("</nav>")
    rendered = rendered[:start] + rendered[end:]
    (directory / name).write_text(rendered)
