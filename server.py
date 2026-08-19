from flask import Flask, request, jsonify         # get the needed class from the flask library
import requests
from flask_cors import CORS #before this line, my page server port 8000 cannot connect my Flask server port 5000, CORS is the permission

######page server port 8000: python -m http.server 8000



app = Flask(__name__)            # create the server object
CORS(app) #all answer will carry a certified marker to pass now

#JSON, a standard way to write structured data, you can read it as dictionary
endpoint = "https://plantmetwiki.bioinformatics.nl/sparql"
wanted_relations = ['isPartOf']

def short_name(value):

    if "#" in value:
        return value.rsplit("#", 1)[1] #split from #, xxxx#xxxx, keep the last words

    elif "/" in value:
        return value.rstrip("/").rsplit("/", 1)[1] #if there is no #, cut at /

    else:
        return value

def get_label(uri):

    label_query = f"""
    SELECT ?label
    WHERE {{
        GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways> {{

            {{
                <{uri}>
                <http://vocabularies.wikipathways.org/gpml#name>
                ?label .
            }}

            UNION

            {{
                <{uri}>
                <http://vocabularies.wikipathways.org/gpml#textlabel>
                ?label .
            }}

        }}
    }}
    LIMIT 1
    """

    response = requests.get(
        endpoint,
        params={
            "query": label_query,
            "format": "application/sparql-results+json"
        }
    )

    data = response.json()

    results = data["results"]["bindings"]

    if len(results) > 0:
        return results[0]["label"]["value"]

    return short_name(uri)


@app.route("/")                  # when someone requests the address "/" ...
def home():
    return "hello from yang"


"""
def graph():
    data = request.get_json()
    row_count = len(data["results"]["bindings"])
    return jsonify({"rows_received": row_count})
"""

@app.route("/graph", methods=["POST"])
def graph():
    data = request.get_json()
    bindings = data["results"]["bindings"]

    nodes = []
    edges = []

    # your filter loop from sparql_test.py:
    for row in bindings:
        s = row["s"]["value"]
        p = row["p"]["value"]
        o = row["o"]["value"]
        o_type = row["o"]["type"]

        relation = short_name(p)

        if (o_type == "uri" and relation in wanted_relations
                and "/Comment/" not in s
                and "/Comment/" not in o):
            nodes.append(s)
            nodes.append(o)
            edges.append({"source": s, "target": o, "label": relation})

    # your dedup:
    nodes = list(dict.fromkeys(nodes))

    # your node list with labels:
    node_list = []
    for node in nodes:
        node_list.append({"id": node, "label": get_label(node)})

    return jsonify({"nodes": node_list, "edges": edges})

app.run(port=5000)               # start the server on port 5000 and wait