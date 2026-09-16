from flask import Flask, request, jsonify
import requests #send a request to web server, and get an answer back
from flask_cors import CORS #before this line, my page server port 8000 cannot connect my Flask server port 5000, CORS is the permission

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
    if "#" in value: #e.g. http://vocabularies.wikipathways.org/wp#Conversion
        return value.rsplit("#", 1)[1]

    elif "/" in value: #https://identifiers.org/Phytozome/AT5G52810.1
        return value.rstrip("/").rsplit("/", 1)[1]

    else: #RDF triples can also carry literal values, e.g. 1-piperideine-2-carboxylate reductase
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

    #the below query mean: try to find a gpml#name or gpml#textlabel in the URI, e.g. a sugar
    label_query = f"""
    SELECT ?label
    WHERE {{
    GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways> {{
        <{uri}> <http://www.w3.org/2000/01/rdf-schema#label> ?label .
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
        )
    except Exception as e:
        print(e)
        return short_name(uri) #the fallback choice of this function

    data = response.json() #turn the output into a dict

    results = data["results"]["bindings"]

    if len(results) > 0:
        label = results[0]["label"]["value"]
        memory[uri] = label
        return label
    else: #at least return something
        last_part_uri = short_name(uri)
        memory[uri] = last_part_uri
        #print(last_part_uri)
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

    #what is this URI's `rdf:type`?
    type_query = f"""
    SELECT DISTINCT ?type
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
        wp_types = [result["type"]["value"] for result in results if
                    'wp#' in result["type"]["value"]]
        if wp_types:
            entity_type = short_name(wp_types[0])
        else: #what if we do not find our preference wp#? like gpml#DataNode
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
    """Turn SPARQL query results (JSON ) into graph nodes and edges.

    return: JSON {"nodes": [...], "edges": [...]}
    """
    data = request.get_json()

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

    nodes = {}
    edges = {}

    for row in data["results"]["bindings"]:
        prev_id = None
        for entity in entity_ls:
            entity_uri = row[entity]['value']
            if entity in label_dict and label_dict[entity] in row:
                entity_id = row[label_dict[entity]]['value']
            else:
                entity_id = get_name(entity_uri) #we cannot get the label for raffinose like this that's why we need above codes
                                                 #10-09 it is solved, by changing the query in get_name() for searching for rdf#label

            if entity_uri not in nodes:
                nodes[entity_uri] = {'id': entity_uri, 'label':entity_id, 'type': get_entity_type(entity_uri)} #uri is unique

            if prev_id: #there is a entity before this loop
                edge_key = (prev_id, entity_uri) #last entity and this entity
                if edge_key not in edges:
                    edges[edge_key] = {'source': prev_id, 'target': entity_uri, 'label':''}

            prev_id = entity_uri

    #JSON dose not accept tuple as key, only string
    #drop out the key, the uri has a copy in the values
    node_list = list(nodes.values())
    edge_list = list(edges.values())
    return jsonify({"nodes": node_list, "edges": edge_list})

if __name__ == '__main__':
    app.run(port=5000)               # start the server on port 5000 and wait