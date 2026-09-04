#imports
from flask import Flask, request, jsonify         # get the needed class from the flask library
import requests #??
from flask_cors import CORS #before this line, my page server port 8000 cannot connect my Flask server port 5000, CORS is the permission

######page server port 8000: python -m http.server 8000

"""Workflow of the graph visualization function

1. You run a query on the main page — results get saved to sessionStorage
2. You click Graph Visualization — the popup opens and reads those saved results
3. The popup's fetch(...) sends those results to http://localhost:5000/graph
4. Flask sees a POST arrive at /graph, and because of the @app.route decorator, runs graph()
5. graph()'s return value (the JSON with nodes/edges) becomes the answer sent back to that fetch call
6. The popup's JavaScript receives it and draws the graph
"""

#setup
app = Flask(__name__)            # create the server object
CORS(app) #all answer will carry a certified marker to pass now

endpoint = "https://plantmetwiki.bioinformatics.nl/sparql" #address, used whenever this server needs to ask it sth.
wanted_relations = ['participants', 'source', 'target'] #only biologcial relation is kept
memory = {} #remember the label
type_memory = {}

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

def get_name(uri):
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

def get_entity_type(uri):
    """Ask the database what type this URI is (via rdf:type / 'a').

    Parameters:
        uri: The URI of one node, as a string.

    Returns: type,
        The short type name (e.g. "Protein", "GeneProduct"), or
        "other" if the database has no type for this URI.
    """

    if uri in type_memory:
        return type_memory[uri]

    type_query = f"""
    SELECT ?type
    WHERE {{
        <{uri}> a ?type .
    }}
    """

    try:
        response = requests.get(
            endpoint,
            params={
                "query": type_query,
                "format": "application/sparql-results+json"
            }
        )
    except Exception as e:
        print(e)
        return "other"

    data = response.json()
    results = data["results"]["bindings"]

    if len(results) > 0:
        wp_types = [r["type"]["value"] for r in results if
                    'wp#' in r["type"]["value"]]
        if wp_types:
            entity_type = short_name(wp_types[0])
        else:
            entity_type = short_name(results[0]["type"]["value"])
    else:
        entity_type = "other"

    type_memory[uri] = entity_type
    return entity_type


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


    var_names = data['head']['vars'] #gene, geneProteinInteraction, protein, proteinlabel etc.

    entity_ls = []
    label_dict = {}

    for name in var_names:
        if name.endswith('Label'):
            try:
                label_dict[entity_ls[-1]] = name
            except IndexError:
                print('missing the first valid column name')
        else:
            entity_ls.append(name)


    nodes = [] #['gene':{"id": value, "label": <label>, "type": type}, 'protein':{xxxx}]
    edges = []
    seen_nodes = set() #avoid duplicate
    seen_edges = set()

    for row in data["results"]["bindings"]:
        prev_id = None
        for entity in entity_ls:
            entity_value_uri = row[entity]['value']
            if entity in label_dict and label_dict[entity] in row:
                entity_id = row[label_dict[entity]]['value']
            else:
                entity_id = get_name(entity_value_uri) #we cannot get the label for raffinose like this that's why we need above codes

            if entity_value_uri not in seen_nodes:
                seen_nodes.add(entity_value_uri)
                nodes.append({'id': entity_value_uri, 'label':entity_id, 'type': get_entity_type(entity_value_uri)}) #uri is unique

            if prev_id is not None: #there is a entity before this loop
                edge_key = (prev_id, entity_value_uri) #last entity and this entity
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({'source': prev_id, 'target': entity_value_uri, 'label':''})

            prev_id = entity_value_uri

    print("NODES:", nodes)
    print("EDGES:", edges)

    return jsonify({"nodes": nodes, "edges": edges})

app.run(port=5000)               # start the server on port 5000 and wait