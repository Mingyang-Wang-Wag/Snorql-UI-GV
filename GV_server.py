from flask import Flask, request, jsonify
import requests #send a request to web server, and get an answer back
from flask_cors import CORS #before this line, my page server port 8000 cannot connect my Flask server port 5000, CORS is the permission
import json
import re
app = Flask(__name__)            # create the server object
CORS(app) #all answer will carry a certified marker to pass now

endpoint_pmw = "https://plantmetwiki.bioinformatics.nl/sparql" #address, used whenever this server needs to ask it sth.
endpoint_local = "http://localhost:8890/sparql"
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
            endpoint_local,
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
        label = results[0]["label"]["value"] #even it only has one element, a dict, it is still a list, the [0] cannot be skipped
        memory[uri] = label
        return label
    else: #if the result is empty, at least return something
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

    #what is this URI's `rdf:type`?
    type_query = f"""
    SELECT DISTINCT ?type
    WHERE {{
        GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways> {{
            <{uri}> a ?type .
        }}
    }}
    """
    #usually, a node will have two types: DataNode and the true type, e.g. protein, metabolite
    try:
        response = requests.get(
            endpoint_local,
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

    entity_type = "other" #other is the default value for entity_type

    if len(results) > 0:
        for result in results:
            if 'wp#' in result['type']['value']:
                candidate_entity_type = short_name(result['type']['value'])
                if candidate_entity_type != 'DataNode':
                    entity_type = candidate_entity_type

                    break #there could be multiple type for one node, even after excluding DataNode, let's put it in this way first.

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
                if entity == "evidence":
                    node_type = "Evidence"
                elif entity == "trait":
                    node_type = "TO"
                else:
                    node_type = get_entity_type(entity_uri)

                nodes[entity_uri] = {
                    "id": entity_uri,
                    "label": entity_id,
                    "type": node_type
                }

            if entity not in ("evidence", "trait"):
                if prev_id:
                    edge_key = (prev_id, entity_uri)
                    if edge_key not in edges:
                        edges[edge_key] = {
                            "source": prev_id,
                            "target": entity_uri,
                            "label": ""
                        }

                prev_id = entity_uri
        for start, end, relation in [
            ("gene", "evidence", "hasEvidence"),
            ("evidence", "trait", "hasOntologyTerm")
        ]:
            if start in row and end in row:
                source = row[start]["value"]
                target = row[end]["value"]
                edges[(source, target)] = {
                    "source": source,
                    "target": target,
                    "label": relation
                }
    #JSON dose not accept tuple as key, only string
    #drop out the key, the uri has a copy in the values
    node_list = list(nodes.values())
    edge_list = list(edges.values())
    return jsonify({"nodes": node_list, "edges": edge_list})

@app.route("/evidence", methods=["GET"])
def get_evidence():
    uri = request.args.get("uri", "").strip()

    if not uri:
        return jsonify({"error": "Missing Evidence URI"}), 400

    if not re.fullmatch(r"urn:pmw-pheno:evidence:AT[1-5MC]G[0-9]{5}", uri):
        return jsonify({"error": "Invalid Evidence URI"}), 400

    query = f"""
        SELECT ?details WHERE {{
            GRAPH <urn:pmw-pheno:graph:tair-evidence> {{
                <{uri}> <urn:pmw-pheno:vocab:alleleDetails> ?details .
            }}
        }}
        LIMIT 1
    """

    try:
        response = requests.get(
            endpoint_local,
            params={
                "query": query,
                "format": "application/sparql-results+json"
            },
            timeout=15
        )
        response.raise_for_status()
        rows = response.json()["results"]["bindings"]

        if not rows:
            return jsonify({"error": "No phenotype details found"}), 404

        alleles = json.loads(rows[0]["details"]["value"])
        return jsonify({"evidence": uri, "alleles": alleles})

    except (requests.RequestException, ValueError, KeyError) as error:
        app.logger.warning("Evidence lookup failed: %s", error)
        return jsonify({"error": "Could not load phenotype details"}), 502

if __name__ == '__main__':
    app.run(port=5000)               # start the server on port 5000 and wait