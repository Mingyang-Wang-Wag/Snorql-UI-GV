# Graph Visualization — Feature Roadmap

This file tracks the step-by-step development of the Graph Visualization feature.
New steps are appended at the bottom.

---

## Long-term goal

Add a "Graph Visualization" button that renders SPARQL query results as an
interactive knowledge graph (e.g., gene → protein → pathway).

**Core principle (decided):** the graph is built from the **raw JSON that the
database returns** (`head.vars` + `results.bindings`) — NOT by converting or
scraping the HTML results table. The existing table rendering stays completely
untouched.

**Not decided yet** (to be chosen in a later step, once the new PlantMetWiki
data is clearer):
- Which graph library to use (vis-network, Cytoscape.js, or something else)
- The exact mapping from query results to nodes and edges

Useful codebase facts for future steps:
- The raw SPARQL JSON arrives in `displayResult(json, title)` in
  `assets/js/snorql.js` (~line 302) and is currently discarded after the table
  is drawn — a cache hook will be needed there.
- All libraries are vendored locally in `assets/` (no CDN at runtime), so any
  graph library must be added as a local file.
- The existing `toQName` helper in `snorql.js` is buggy (iterates prefixes but
  indexes by URI) — write a fresh prefix-shortening helper when node labels
  are needed.

---

## Step 1 (DONE) — Button that shows a word

Added the `#graph-viz-button` button to the toolbar in `index.html`.
Clicking it toggled a hidden panel showing the word "apple" below the query
box. Purpose: establish the button and wiring with the smallest possible step.

The panel was removed again in Step 2 (replaced by the popup window).

---

## Step 2 (DONE) — Popup window showing the query text

Clicking "Graph Visualization" now opens a small separate window (~700×500)
showing the SPARQL query currently typed in the editor.

Changes:
- `index.html` — removed the Step 1 "apple" panel; button stays
- `graph.html` (NEW) — the popup page; will host the graph canvas in later
  steps. For now it displays the query text in a gray box.
- `assets/js/script.js` — button handler saves the editor text to
  `sessionStorage` (key `graphVizQuery`) and opens `graph.html` via
  `window.open`. The popup reads the text from `sessionStorage` on load.
  The named window `"graphVizWindow"` is reused on repeated clicks.

Why sessionStorage: the popup is a separate page and cannot see the main
page's editor directly. sessionStorage is shared between pages of the same
site — the main page writes the query, the popup reads it. This avoids URL
length limits (SPARQL queries can be long) and fragile `window.opener`
coupling.

---

## Step 3 (DONE) — Connect to PlantMetWiki + popup shows the raw database output

Changes:
- `assets/js/snorql.js` (lines 1-2) — default endpoint changed from WikiPathways
  to `https://sparql-plantmetwiki.bioinformatics.nl/sparql`, default examples
  repo to `https://github.com/pathway-lod/SPARQLQueries`. (In Docker these are
  overwritten from `.env` anyway; this makes local development match.)
- `assets/js/snorql.js` (`displayResult`) — when query results arrive, a copy
  of the raw SPARQL JSON is saved to sessionStorage (key `graphVizResults`),
  guarded by try/catch so oversized results never break the table.
- `graph.html` — now also shows the raw database output (pretty-printed JSON)
  below the query text. This JSON is exactly the data the graph will be built
  from in the next step.

---

## Development strategy: demo first, schema later (decided 2026-08-18)

Question: before building the real graph, should we first design the new data
schema, download the data from the source websites, and integrate it — or
build a graph visualization demo first?

**Decision: build the demo first, with the current PlantMetWiki data.**

Reasons:

1. **The demo does not depend on the new data.** The graph code reads whatever
   the database returns — variable names + values. It works the same whether
   the database contains today's data or the future integrated data. When the
   new schema lands, the same graph simply shows richer content.

2. **The demo answers the risky unknowns early.** Which library? Does
   rendering work in this old jQuery stack? How should results map to nodes
   and edges? These are the parts most likely to surprise. Schema design and
   data integration are big but well-understood work — they rarely fail in
   surprising ways.

3. **Schema design benefits from the demo existing.** Once query results are
   visible as a graph, awkward spots become obvious ("the protein should link
   to its pathway directly", "labels are needed, not URIs"). Those
   observations should inform the schema design; doing schema first means
   designing blind.

4. **For the thesis, it gives a working prototype early.** A visible demo to
   show the supervisor beats a perfect schema nobody can see, and
   "prototype → feedback → schema refinement → final integration" is a
   textbook iterative methodology chapter.

Order of work:

1. **Now:** finish the demo pipeline in small steps — popup shows the raw
   database JSON → popup draws a simple graph from it (current data)
2. **Then:** design the schema, informed by what the demo taught us
3. **Then:** download + integrate the new data
4. **Finally:** tune the graph (mapping, colors, labels) to the real schema

This resolves the earlier open question of whether the data work should come
first.

---

## Step 4 (partly done, then superseded) — Draw the graph in the popup

Library note (2026-08-18): **Cytoscape.js** (v3.30.4, MIT) was vendored as
`assets/js/cytoscape.min.js` and proven working:
- [x] 4a. Load Cytoscape in graph.html, draw a hard-coded test graph
      (two circles + one arrow) — proves the library works

The remaining sub-steps (4b-4f, building the graph in JavaScript) were
**superseded by the architecture pivot below** before implementation.

---

## ARCHITECTURE PIVOT (decided 2026-08-18) — Python-first pipeline

The user built an independent Python prototype (`sparql_test.py` +
vis-network `graph.html` + `graph_data.json`) and set the direction:
**use Python as much as possible, JavaScript as little as possible.**
JavaScript cannot be avoided entirely (browsers only run JavaScript), so the
split is: **Python does all the thinking, JavaScript only draws.**

### The agreed data flow

```
1. User types a working query in Snorql-UI, presses Query
2. The database answers (raw SPARQL JSON)
3. A COPY of that JSON is sent to Python            ← browser → Flask server
4. Python parses it and extracts the key info        ← all logic in Python:
   (filter relations e.g. isPartOf, skip /Comment/,    reuses the prototype's
   look up labels via gpml#name/textlabel,             short_name, get_label,
   deduplicate nodes)                                  filter loop, dedup
5. Python returns the finished {nodes, edges}
6. The popup draws them — AND also shows the query text (user explicitly
   likes this: the popup displays the query it belongs to)
```

Key facts supporting this design:
- Step 2→3 is half-built already: `displayResult` in snorql.js copies every
  query answer into sessionStorage; the popup already holds the JSON.
- "Send to Python" requires Python to run as a **server** (a program that
  stays running and waits for requests — like Virtuoso). Tool: **Flask**.
- Demo assumption: the query selects `?s ?p ?o` (the parsing code reads
  row["s"], row["p"], row["o"]). Arbitrary columns = later, pure-Python work.
- Drawing library: **vis-network** (reuses the user's working prototype
  drawing code). The vendored Cytoscape file stays as a fallback option.

### Step 5 — Flask pipeline (one small step at a time, user tests each)

- [x] A. Install Flask; run the smallest possible server ("hello" in browser) — done 2026-08-18, server.py in project root
- [x] B. Server receives JSON via POST and returns a tiny answer — done 2026-08-18
      (learned along the way: a server is a running copy of the file; restart after edits)
- [x] C. Move the prototype's parsing (short_name, get_label, filter, dedup)
      into the server: input = SPARQL results JSON, output = {nodes, edges}
      — done 2026-08-18; verified with real PlantMetWiki data (Sugar --isPartOf--> Thioglucosidase)
- [x] D1. Popup sends the stored results JSON to the server and displays the
      server's answer as text (CORS enabled via flask-cors) — done 2026-08-18.
      Fixes along the way: endpoint default corrected to
      https://plantmetwiki.bioinformatics.nl/sparql (snorql.js line 3; the
      sparql- subdomain variant didn't work); learned that the URL ?endpoint=
      parameter overrides the default, and that the browser caches .js files
      (Ctrl+F5 forces a fresh copy)
- [x] D2. Draw the server's answer as a graph — done 2026-08-18. Library:
      Cytoscape.js (already vendored; the vis-network idea was dropped).
      The popup shows: the graph, the server's JSON answer, the query text,
      and the raw database output. FULL PIPELINE WORKING END TO END:
      query box → Virtuoso → sessionStorage copy → popup → fetch POST →
      Flask (:5000) → parse/filter/label in Python → {nodes, edges} →
      Cytoscape drawing ("a sugar" --isPartOf--> "Thioglucosidase")
- After the demo: schema design → data download/integration → graph tuning

---

## PHASE SHIFT (2026-08-19, after supervisor feedback)

Supervisor + user agreed: the code/visualization part is the more
straightforward piece; the core thesis work is **new data introduction and
integration** into PlantMetWiki. Focus moves there now.

The graph pipeline stays as-is (working demo, committed) and will be tuned
again once the new data is in. Coming work is Python-centric:
1. Identify and download the new source data
2. Design the schema: entity types, relations, how new data links to the
   existing PlantMetWiki structure (building on earlier findings: isPartOf /
   hasDataNode are the meaningful relations; /Comment/ and GPML drawing
   metadata are noise)
3. Transform the source data to RDF matching the schema
4. Load it into PlantMetWiki (Virtuoso)
5. Revisit the graph visualization with the richer data

---

## Step 6 (Done, 2026-08-26) — Handle any query, not just ?s ?p ?o

2026-08-25: make `graph()` in `server.py` work with any SPARQL query
that returns at least 3 columns — not just ones literally named `s`, `p`, `o`.

2026-08-26: Fixed: reads column names from data["head"]["vars"] instead of 
hardcoding row["s"]/["p"]/["o"] (anything else will crash); tested with both 
the original ?s ?p ?o query and a renamed ?gene ?relation ?target  version.

But still need at least 3 columns, always treat column 1, 2, 3 as subject,
predicate and target individually.

## Step 7 (Done, 2026-08-26) -- adding one more relation, hasDadaNode
2026-08-26: added `hasDataNode` to wanted_relations — confirmed a new 
hasDataNode edge appears in the graph.
why add these two?
because these two were specifically identified as the biological meaningful one
everything else risks being noise, like drawing coordinates, GPML layout info.


2026-08-27: visual polish — bigger nodes with labels below, gray/thinner edges. 
Tested, confirmed working.

2026-08-28: wanted_relations changed to biological-only relations: ['participants', 'source', 'target'] 
(removed isPartOf, hasDataNode — confirmed structural via vocabulary lookup). 
Verified with Chalcone Isomerase reaction — shows real participants/target edges.

2026-08-28: fixed duplicate edges — added seen_edges set to dedupe on (subject, relation, object). 
Tested with a UNION query that deliberately doubles every triple; confirmed edges still appear only once.

2026-08-31: get_label(uri) function ask database same question for every node, which takes much time when we have lots of nodes.
What the fix does: the first time we ask about some URI, we write down the answer. 
The next time that exact same URI comes up — anywhere, anytime — we just read what we already wrote down, instantly, instead of asking the database again.
Done

2026-08-31:
get_label(uri):
response = requests.get(endpoint, params={...})
data = response.json()

If this request fails for any reason — timeout, connection error, 
or the server sending back something that isn't valid JSON — Python raises 
an exception here. Since nothing catches it, that exception travels all the 
way up and crashes the entire /graph request with a 500 error.

fix: wrap this request in a try/except
Tested by temporarily pointing endpoint at a broken address; 
confirmed graceful fallback labels instead of a crash.

2026-08-31: verified /Comment/ filter is currently dead code (zero triples with 
participants/source/target touch a Comment node) — kept intentionally as a 
defensive safety net for future relation changes.

2026-01-09: Schema of plantmetwiki show a chain of node connected by edges, 
our current parser does not suppprt to show such pattern. We need to redesign 
the parser. 
Right now graph() only understands ONE shape of query — exactly 3 columns, 
where column 2's value must be a relation name from a fixed list (isPartOf, 
participants, etc.). Any query shaped differently — like your raffinose one 
with 8 columns — gets rejected/ignored, even though it's a perfectly valid, 
meaningful query.
Later on, Double-click-to-expand is that same mechanism again, but triggered 
interactively instead of written into a query upfront: using your example — 
user runs a simple gene → protein query, sees that one-hop graph. Double-clicks 
protein. That click tells the server: "find what's connected to this specific 
node" — the server auto-builds a small query centered on that protein's URI 
(using participants/source/target, same as always), gets back the next hop (the 
reaction, maybe other genes), and merges those new nodes into the existing graph 
instead of replacing it.