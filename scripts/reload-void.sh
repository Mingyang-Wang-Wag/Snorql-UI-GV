#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Reload ONLY the VoID graph (<…/void>) in the local Virtuoso, from the VoID
# files in db/data/. Use after regenerating VoID (e.g. to pick up a corrected
# void:sparqlEndpoint or the sd:Service) without touching the data graphs.
#
# The /void graph aggregates every void-*.ttl in db/data/:
#   - void-*.ttl        (gpml-to-rdf core VoID + BridgeDb void:Linkset + sd:Service)
#   - void-bgc*.ttl     (map-to-rdf BGC VoID)
#   - void-ncbitaxon*.ttl (create-ncbitaxon-void.sh output, if present)
#
# Usage:
#   bash scripts/reload-void.sh
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/db/data"
BASE_GRAPH="http://rdf-plantmetwiki.bioinformatics.nl"
VOID_GRAPH="${BASE_GRAPH}/void"

# Load .env (VIRTUOSO_CONTAINER, VIRTUOSO_PASSWORD) if present
[ -f "$SCRIPT_DIR/../.env" ] && set -a && . "$SCRIPT_DIR/../.env" && set +a
CN="${VIRTUOSO_CONTAINER:-plantmetwiki-virtuoso}"
PW="${VIRTUOSO_PASSWORD:-dba123}"

shopt -s nullglob
void_files=("$DATA_DIR"/void-*.ttl)
if [ ${#void_files[@]} -eq 0 ]; then
  echo "ERROR: no void-*.ttl files in $DATA_DIR" >&2
  echo "       Download (download-plantmetwiki-data.py) or regenerate VoID first." >&2
  exit 1
fi

echo "Reloading <$VOID_GRAPH> from:"
printf '  %s\n' "${void_files[@]}"

# Clear the VoID graph once, then load every void file into it.
docker exec -i "$CN" isql 1111 dba "$PW" <<SQL
SPARQL CLEAR GRAPH <$VOID_GRAPH>;
SQL

for f in "${void_files[@]}"; do
  fname="$(basename "$f")"
  docker cp "$f" "$CN:/tmp/$fname"
  docker exec -i "$CN" isql 1111 dba "$PW" <<SQL
ld_dir('/tmp', '$fname', '$VOID_GRAPH');
rdf_loader_run();
checkpoint;
DELETE FROM DB.DBA.LOAD_LIST WHERE ll_file = '/tmp/$fname';
SQL
  docker exec "$CN" rm -f "/tmp/$fname"
done

# Report
n=$(docker exec -i "$CN" isql 1111 dba "$PW" <<SQL | grep -Eo '[0-9]+' | tail -1
SPARQL SELECT (COUNT(*) AS ?n) WHERE { GRAPH <$VOID_GRAPH> { ?s ?p ?o } };
SQL
)
echo "Done. <$VOID_GRAPH> now holds ${n:-?} triples."
echo "Verify the canonical endpoint + service description:"
echo "  ?d void:sparqlEndpoint <$( echo "$BASE_GRAPH" | sed 's|rdf-plantmetwiki|plantmetwiki|' )>  (expect plantmetwiki.bioinformatics.nl/sparql)"
