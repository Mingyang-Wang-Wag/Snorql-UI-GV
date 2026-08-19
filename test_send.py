import requests

endpoint = "https://plantmetwiki.bioinformatics.nl/sparql"

# find all things connect to sugar
query_sugar = """
SELECT ?s ?p ?o
WHERE {
    GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways> {

        {
            BIND(
                <http://rdf-plantmetwiki.bioinformatics.nl/Pathway/RC1000_r17.0.0_20260605-171052/DataNode/Sugar>
                AS ?s
            )

            ?s ?p ?o .
        }

        UNION

        {
            ?s ?p
                <http://rdf-plantmetwiki.bioinformatics.nl/Pathway/RC1000_r17.0.0_20260605-171052/DataNode/Sugar> .

            BIND(
                <http://rdf-plantmetwiki.bioinformatics.nl/Pathway/RC1000_r17.0.0_20260605-171052/DataNode/Sugar>
                AS ?o
            )
        }
    }
}
LIMIT 30
"""

# 1. run the query (this is what Snorql-UI normally does)
r1 = requests.get(endpoint, params={"query": query_sugar,
                                    "format": "application/sparql-results+json"})
results = r1.json()

# 2. send the results to your server (this is what the popup will do)
r2 = requests.post("http://localhost:5000/graph", json=results)
print(r2.status_code)
print(r2.json())