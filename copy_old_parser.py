import requests
import json






#give me five triples (subject - verb - object) from plantmetwiki
query_test = """
SELECT ?s ?p ?o
WHERE {
    GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways> {
        ?s ?p ?o
    }
}
LIMIT 5
"""

#find all things that connect to sugar
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

#here we need to check what RC1000_r17.0.0_20260605-171052 really is, because we got sugar -> RC1000, but what RC1000 really is
query_RC1000_pathway = """
SELECT ?p ?o
WHERE {
    GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways> {

        <http://rdf-plantmetwiki.bioinformatics.nl/Pathway/RC1000_r17.0.0_20260605-171052>
        ?p ?o .

    }
}
LIMIT 30
"""

#send this SPARQL to plantmetwiki
response = requests.get(
    endpoint,
    params={
        "query": query_sugar,
        "format": "application/sparql-results+json"
    }
)

response.raise_for_status()

#take PlantMetWiki's JSON answer and turn it into something Python can understand.
data = response.json()

bindings = data["results"]["bindings"]


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


#store the nodes and edges
nodes = []
edges = []

wanted_relations = [
    "isPartOf",
]

#we want useful biological connection
#same relationship can be written in opposite direciton, A to B, B to A.



for row in bindings: # in bindings contain the RDF URIs, so we only need bindings
    s = row["s"]["value"]
    p = row["p"]["value"]
    o = row["o"]["value"]

    s_type = row["s"]["type"]
    o_type = row["o"]["type"]

    #print(
    #    short_name(s),
    #    "--", short_name(p), "-->",
    #    short_name(o)
    #)

    #print("SUBJECT:", s)
    #print("PREDICATE:", p)
    #print("OBJECT:", o)

    #if s_type == "uri": #only append when it is url, otherwise the attribute (not just the name) of the node will be also appended
        #nodes.append(s) #RDF contain biological info and GPML drawing info
    #if o_type == "uri":
        #nodes.append(o)

    relation = short_name(p) #after parsing from the url, e.g. ispartof

    if (o_type == "uri" and relation in wanted_relations
            and '/Comment/' not in s
            and '/Comment/' not in o): #if it is useful and the relation is the useful one

        nodes.append(s)
        nodes.append(o)

        edges.append({
            "source": s,
            "target": o,
            "label": relation
        })


#print("NODES:")
#print(nodes)

#print("\nEDGES:")
#print(edges)


#print(json.dumps(data, indent=2))


#we found in our nodes, there are some occurs more than once, we prefer to have
#three different nodes all points to one node, instead of three different nodes
#points to three nodes but these three nodes are actually the same one.

nodes = list(dict.fromkeys(nodes)) #convert the list into dictionary's key, the
#key cannot be duplicate, then convert back to list.

node_list = []

for node in nodes:
    node_dict = {
        "id": node, #now the id is the same with label, but in future id will be the url and label is the short name
                    #id will be for computer, label will be shown to human
        "label": get_label(node)
    }

    node_list.append(node_dict)

graph_data = {
    "nodes": node_list,
    "edges": edges
}

print(node_list)

print("\nEDGES:")

for edge in edges:
    print(
        short_name(edge["source"]),
        "--", edge["label"], "-->",
        get_label(edge["target"])
    )

#plantmetwiki mixed 1. biological info 2. database/identifier metedata 3. drawing instruction together
#and what is useful is: isPartOf, hasDataNode


#save the result to JSON
graph_data = {
    "nodes": node_list,
    "edges": edges
}

with open("graph_data.json", "w", encoding="utf-8") as f:
    json.dump(graph_data, f, indent=2, ensure_ascii=False)

print("Graph data saved.")