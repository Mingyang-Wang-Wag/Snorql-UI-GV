#imports
from flask import Flask, request, jsonify         # get the needed class from the flask library
import requests #??
from flask_cors import CORS #before this line, my page server port 8000 cannot connect my Flask server port 5000, CORS is the permission

######page server port 8000: python -m http.server 8000


#setup
app = Flask(__name__)            # create the server object
CORS(app) #all answer will carry a certified marker to pass now

endpoint = "https://plantmetwiki.bioinformatics.nl/sparql" #address, used whenever this server needs to ask it sth.
wanted_relations = ['isPartOf'] #the only relation kept

def short_name(value):
    """Takes a long URI and returns just last part

    return: str, e.g. http://xxx/gpml#isPartOf → isPartOf
    """
    if "#" in value:
        return value.rsplit("#", 1)[1] #split from #, xxxx#xxxx, keep the last words

    elif "/" in value:
        return value.rstrip("/").rsplit("/", 1)[1] #remove the last /, right split at / once

    else:
        return value

def get_label(uri):
    """Find the human-readable name for a URI.

    Parameters:
        uri: The URI of one node, as a string.

    Returns: label,
        The label text found for the URI (from gpml:name or
        gpml:textlabel), or the URI's last path segment if no
        label was found.
    """

    #the below query mean: try to find a gpml#name or gpml#textbael in the URI
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

    data = response.json() #turn the output into a dict

    results = data["results"]["bindings"]

    if len(results) > 0:
        return results[0]["label"]["value"]

    return short_name(uri)


@app.route("/")                  #printing sth, proving the server is alive
def home():
    return "hello from yang"

@app.route("/graph", methods=["POST"]) #when the server receive a POST, run the function below
def graph():
    """Turn SPARQL query results (sent as JSON in the POST body) into graph
    nodes and edges.

    return: JSON {"nodes": [...], "edges": [...]}
    """
    data = request.get_json()
    '''
    data                                    dict  (keys: "head", "results")
    └── data["results"]                     dict  (key: "bindings")
        └── data["results"]["bindings"]     LIST  ← not a dict! one item per row
            └── bindings[0]  (= "row")      dict  (keys: "s", "p", "o")
                └── row["s"]                dict  (keys: "type", "value")
                    └── row["s"]["value"]   a plain string ← the actual data
    '''
    bindings = data["results"]["bindings"]

    nodes = []
    edges = []

    # your filter loop from sparql_test.py:
    for row in bindings:
        s = row["s"]["value"] #check the column named 's' and its value (not type)
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