#imports
from flask import Flask, request, jsonify         # get the needed class from the flask library
import requests #??
from flask_cors import CORS #before this line, my page server port 8000 cannot connect my Flask server port 5000, CORS is the permission

######page server port 8000: python -m http.server 8000


#setup
app = Flask(__name__)            # create the server object
CORS(app) #all answer will carry a certified marker to pass now

endpoint = "https://plantmetwiki.bioinformatics.nl/sparql" #address, used whenever this server needs to ask it sth.
wanted_relations = ['participants', 'source', 'target'] #only biologcial relation is kept
memory = {} #remember the label


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

    if uri in memory:
        #print("CACHED:", uri) #Testing: it should be printed after query and second time you open the graph visualization.
        return memory[uri] #if uri is already stored, just show it.

    #the below query mean: try to find a gpml#name or gpml#textbael in the URI, e.g. a sugar
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

    try:
        response = requests.get(
            endpoint,
            params={
                "query": label_query,
                "format": "application/sparql-results+json"
            }
        ) #send the query
    except Exception as e:
        print(e)
        return short_name(uri) #the fallback choice of this function

    #print("LOOKED UP:", uri) #testing: after query, first time click graph visualization

    data = response.json() #turn the output into a dict

    results = data["results"]["bindings"]

    if len(results) > 0:
        label = results[0]["label"]["value"]
        memory[uri] = label
        return label
    else: #if nothing come back, means no gpml#name or gpml#textlabel for this URI, return the last part of the URI, something is better than nothing.
        last_part_uri = short_name(uri)
        memory[uri] = last_part_uri
        return last_part_uri



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


    var_names = data['head']['vars']

    if len(var_names) < 3:
        return jsonify({'error': 'need at least 3 columns'}), 400 #build a JSON reponse, holding error message instead of nodes/edges

    subject_var = var_names[0]
    predicate_var = var_names[1]
    object_var = var_names[2]

    bindings = data["results"]["bindings"]

    nodes = []
    edges = []
    seen_edges = set() #avoid duplicate edges

    # your filter loop from sparql_test.py:
    for row in bindings:
        s = row[subject_var]["value"] #check the column named 's' and its value (not type)
        p = row[predicate_var]["value"]
        o = row[object_var]["value"]
        o_type = row[object_var]["type"]

        relation = short_name(p)

        if (o_type == "uri" and relation in wanted_relations
                and "/Comment/" not in s
                and "/Comment/" not in o): #must all be true
            '''
            o_type == "uri" — the object is a link to another entity, not plain text
            relation in wanted_relations — the predicate is one of the approved biological relations (participants/source/target)
            "/Comment/" not in s — the subject's URI text doesn't contain /Comment/
            "/Comment/" not in o — same check on the object
            but comment node (/comment/ does not have any participants/source/target, the last two conditions are dead code
            
            Comment is a text note attached to a pathway element (like a footnote), not a biological entity. 
            Comment nodes have URIs containing /Comment/ in the path. 
            '''
            nodes.append(s) #add as a node
            nodes.append(o)

            edges_key = (s, relation, o) #store the node - edge -node as a triple in tuple

            if edges_key not in seen_edges: #each triple only store once, only by then append the new edge
                seen_edges.add(edges_key)
                edges.append({"source": s, "target": o, "label": relation})

    # your dedup:
    nodes = list(dict.fromkeys(nodes))

    # your node list with labels:
    node_list = []
    for node in nodes:
        node_list.append({"id": node, "label": get_label(node)})

    return jsonify({"nodes": node_list, "edges": edges})

app.run(port=5000)               # start the server on port 5000 and wait