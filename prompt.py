system_prompt = """You translate English questions into SPARQL queries for the PlantMetWiki database
"""

schema_prompt = """
Schema: PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"""


query_prompt_protein = """
Example query for uniprot_id of Q9FND9:

PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT
    ?gene
    ?protein
    ?proteinLabel
    ?product
    ?productLabel

WHERE {
    VALUES ?protein {
        <https://identifiers.org/uniprot/Q9FND9>
    }

    ?geneProteinInteraction
        wp:source ?gene ;
        wp:target ?protein .

    OPTIONAL {
        ?protein rdfs:label ?proteinLabel .
    }

    ?enzymeReactionInteraction
        wp:source ?protein ;
        wp:target ?conversion .

    ?conversion a wp:Conversion .

    ?conversion
        wp:target ?product .

    OPTIONAL {
        ?product rdfs:label ?productLabel .
    }
}
ORDER BY ?product
"""

query_prompt_gene = """
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT
    ?gene
    ?protein
    ?proteinLabel
    ?product
    ?productLabel

WHERE {
    VALUES ?gene {
        <https://identifiers.org/tair.name/AT5G40390>
    }

    ?geneProteinInteraction
        wp:source ?gene ;
        wp:target ?protein .

    ?protein a wp:Protein .

    OPTIONAL {
        ?protein rdfs:label ?proteinLabel .
    }

    ?enzymeReactionInteraction
        wp:source ?protein ;
        wp:target ?conversion .

    ?conversion a wp:Conversion .

    ?conversion
        wp:target ?product .

    OPTIONAL {
        ?product rdfs:label ?productLabel .
    }
}
ORDER BY ?product
"""


