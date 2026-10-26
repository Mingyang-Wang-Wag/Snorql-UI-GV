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
    entity_type = "other"  # other is the default value for entity_type

    if uri in type_memory:
        return type_memory[uri]
    # for TO and Evidence only, because the URI is defined by us, the prefix are unique
    elif uri.startswith("http://purl.obolibrary.org/obo/TO_"):
        entity_type = 'TO'
        type_memory[uri] = entity_type
        return entity_type

    elif uri.startswith("urn:pmw-pheno:evidence:"):
        entity_type = 'Evidence'
        type_memory[uri] = entity_type
        return entity_type

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
    except Exception as e: #when virtuoso has a problem, python cannot connect to the server
        return "other"

    data = response.json()
    results = data["results"]["bindings"]

    if len(results) > 0:
        for result in results:
            if 'wp#' in result['type']['value']:
                candidate_entity_type = short_name(result['type']['value'])
                if candidate_entity_type != 'DataNode':
                    entity_type = candidate_entity_type

                    break #there could be multiple type for one node, even after excluding DataNode, let's put it in this way first.

    type_memory[uri] = entity_type
    return entity_type

def separate_columns(var_names):
    """Separate entity columns from their matching Label columns.
    input: a list of string, for example [gene, geneProteinInteraction, protein, proteinLabel, reaction, reactionLabel ]

    return: a list of entity names, a dict with entity name: entityLabel
    """
    entity_ls = []
    label_dict = {}

    for name in var_names:
        if name.endswith('Label'):
            continue
        else:
            entity_ls.append(name)

    for name in var_names:
        if name.endswith('Label'):
            entity_name = name[:-5]
            if entity_name in entity_ls:
                label_dict[entity_name] = name

    return entity_ls, label_dict

def get_interaction(source_uri, target_uri):
    """Find the interaction node between two entity (if it exists, because some entity only has direct connection)
    input: two valid URI of entity, str

    return: a list, if it exists, then return a list of str, if nothing, an empty list
    """
    interaction_ls = []
    interaction_query = f"""
    PREFIX wp: <http://vocabularies.wikipathways.org/wp#>

    SELECT DISTINCT ?interactionType
    WHERE {{
    GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways> {{
        ?interaction
            wp:source <{source_uri}> ;
            wp:target <{target_uri}> ;
            a ?interactionType .
        }}
    }}
    """
    try:
        response = requests.get(
            endpoint_local,
            params = {
                "query" : interaction_query,
                "format": "application/sparql-results+json"
            }
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print("Interaction query failed:", e)
        raise
    data = response.json()
    interactions = data['results']['bindings']

    if len(interactions) > 0:
        for interaction in interactions:
            name = short_name(interaction['interactionType']['value'])
            interaction_ls.append(name)

    return interaction_ls


def make_nodes(rows, entity_ls, label_dict):
    """Build a dictionary of unique graph nodes."""
    nodes = {}

    for row in rows:
        for entity in entity_ls:
            entity_uri = row[entity]["value"]

            if entity_uri in nodes:
                continue

            if entity in label_dict and label_dict[entity] in row:
                entity_label = row[label_dict[entity]]["value"]
            else:
                entity_label = get_name(entity_uri)

            nodes[entity_uri] = {
                "id": entity_uri,
                "label": entity_label,
                "type": get_entity_type(entity_uri)
            }

    return nodes

@app.route("/graph", methods=["POST"]) #when the server receive a POST, run the function below
def graph():
    """Turn SPARQL query results (JSON ) into graph nodes and edges.

    return: JSON {"nodes": [...], "edges": [...]}
    """
    data = request.get_json()

    var_names = data['head']['vars']
    entity_ls, label_dict  = separate_columns(var_names)

    nodes = make_nodes(data["results"]["bindings"], entity_ls, label_dict)

    edges = {}
    for row in data["results"]["bindings"]:
        prev_uri = None
        for entity in entity_ls:
            entity_uri = row[entity]['value']
            if entity not in ("evidence", "trait", "substrate", "product"):
                if prev_uri:
                    edge_key = (prev_uri, entity_uri)
                    if edge_key not in edges:
                        interaction_ls = get_interaction(prev_uri, entity_uri)
                        if interaction_ls:
                            interaction_label = ""
                            if 'Catalysis' in interaction_ls: #unique interaction node between protein and reaction
                                interaction_label = 'Catalysis'
                            elif 'TranscriptionTranslation' in interaction_ls: #unique interaction node between gene and protein
                                interaction_label = 'TranscriptionTranslation'
                            edges[edge_key] = {
                                "source": prev_uri,
                                "target": entity_uri,
                                "label": interaction_label
                            }

                prev_uri = entity_uri

        for start, end, relation in [
            ("gene", "evidence", "hasEvidence"),
            ("evidence", "trait", "hasOntologyTerm"),
            ("reaction", "substrate", "hasSubstrate"),
            ("reaction", "product", "hasProduct")

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