#System_prompt should define what the model do and which rule should be followed

# Adapted from LangChain and SIB SPARQL-LLM, with PMW+ specific rules.
system_prompt = """
Translate the user's English question into a read-only SPARQL 1.1 SELECT query for PlantMetWiki+.
Use only the node types and properties provided in the schema.
Use the supplied query examples as references, adapting them to the user's question.
Include all necessary prefixes.
Do not invent entity identifiers or named graph URIs.
On success, return only the query, without Markdown code fences or explanations.
If essential information is missing, return only a comment starting with "# Cannot generate:" explaining what is missing.
"""

#show the the node, edge exactly.
schema_prompt = """
Use the following PlantMetWiki+ schema to generate queries.
Combine only the patterns needed to answer the user's question.

PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX tairp: <urn:pmw-pheno:vocab:>
PREFIX TO: <http://purl.obolibrary.org/obo/TO_>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX pmw: <http://rdf-plantmetwiki.bioinformatics.nl/vocab/>

1. ENTITY TYPES

- Arabidopsis AGI gene: wp:GeneProduct
- Protein: wp:Protein
- Metabolite: wp:Metabolite
- Reaction: wp:Conversion
- Pathway: wp:Pathway
- Evidence: tairp:Evidence; one phenotype-record collection per gene.
- TO term: owl:Class in the TO: namespace.

Substrate and product are reaction roles, not separate node types.
Nodes may have multiple types; use the relevant specific type.

2. GENE, PROTEIN AND REACTION

Both connections use interaction nodes.

GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways> {
    ?gene a wp:GeneProduct .
    ?protein a wp:Protein .
    ?reaction a wp:Conversion .

    # Gene to protein
    ?geneProteinInteraction
        a wp:TranscriptionTranslation ;
        wp:source ?gene ;
        wp:target ?protein .

    # Protein to reaction
    ?catalysis
        a wp:Catalysis ;
        wp:source ?protein ;
        wp:target ?reaction .
}

3. REACTION, SUBSTRATE AND PRODUCT

Use the relevant patterns inside:
GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways>

# Substrate and product
?reaction a wp:Conversion ;
    wp:source ?substrate ;
    wp:target ?product .

# Metabolite on either side
?reaction a wp:Conversion .
?reaction (wp:source|wp:target) ?metabolite .

# Product-to-substrate connection between distinct reaction nodes
?reaction1 a wp:Conversion ;
    wp:target ?intermediate .
?reaction2 a wp:Conversion ;
    wp:source ?intermediate .
FILTER(?reaction1 != ?reaction2)

wp:participants records participation without specifying the role.
Graph connectivity alone does not establish flux or causality.

4. PATHWAY MEMBERSHIP AND NAMES

Use the relevant patterns inside:
GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways>

# Membership: ?entity may be a gene, protein, metabolite or reaction
?entity dcterms:isPartOf ?pathway .
?pathway a wp:Pathway .

# Pathway name
?pathway dc:title ?pathwayName .

# Gene, protein or metabolite name
?entity rdfs:label ?label .

Use OPTIONAL for names used only for display, not as search conditions.

5. GENE AND PHENOTYPE EVIDENCE

Use the relevant patterns inside:
GRAPH <urn:pmw-pheno:graph:tair-evidence>

?gene tairp:hasEvidence ?evidence .
?evidence a tairp:Evidence ;
    tairp:alleleDetails ?details .

One Evidence collection per imported gene.
Other Evidence properties:
- rdfs:label: collection name.
- tairp:alleleCount: allele-group count.
- tairp:recordCount: phenotype-record count.
- tairp:source: dataset source/version.

alleleDetails is a JSON string grouping records by alleleName.
Records include description, metabolicPhenotype, germplasmName,
sourceRecordURI, sourceRecordID, source, ontologyTerms,
and available pmid/doi.

JSON fields are not RDF predicates or separate nodes.
Retrieve ?details for JSON parsing outside SPARQL.


6. EVIDENCE AND TO TRAITS

Use the relevant patterns inside:
GRAPH <urn:pmw-pheno:graph:tair-evidence_to>

?evidence tairp:hasOntologyTerm ?trait .
?trait a owl:Class ;
    rdfs:label ?traitLabel .

# Trait definition
?trait obo:IAO_0000115 ?definition .

Join the two graphs using the same ?evidence.
A TO link means at least one record has that annotation,
not that every allele has the trait.

Use OPTIONAL around the TO lookup when retaining genes
without TO annotations.

The TO graph contains selected terms, labels and definitions,
without a TO hierarchy.
Change direction (increase/decrease) remains in phenotype text.

7. ORGANISM ANNOTATIONS

Use only the relevant patterns below.

# Gene/protein types
GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways> {
    ?gene a wp:GeneProduct .
    ?protein a wp:Protein .
}

# Gene/protein organism
GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/gpml-taxonomy-extra> {
    ?gene wp:organism ?geneTaxon .
    ?protein wp:organism ?proteinTaxon .
}

Arabidopsis thaliana: obo:NCBITaxon_3702

# Pathway organism
GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways> {
    ?pathway a wp:Pathway ;
        wp:organism ?pathwayTaxon .
    OPTIONAL { ?pathway wp:organismName ?organismName . }
}

Pathway taxa may be broader than the taxa of their genes/proteins.

8. ORIGINAL PMW SOURCE METADATA

# Link an entity to its original GPML representation
GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways> {
    ?entity wp:isAbout ?sourceNode .
}

# Read source properties
GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/gpml-properties-extra> {
    ?sourceNode pmw:gpmlProperty ?propertyNode .
    ?propertyNode pmw:key ?key ;
                  pmw:value ?value .
}

Example reaction key strings:
"EC_Number", "ReactionEquation", "ReactionDirection", "UniqueID".

Use OPTIONAL for this lookup when metadata is supplementary.
ReactionEquation is stored as text, not RDF connections.

9. IDENTIFIER RULES

URI templates; replace placeholders with known identifiers:

- AGI gene: <https://identifiers.org/tair.name/{AGI}>
- UniProt protein: <https://identifiers.org/uniprot/{accession}>
- TAIR protein model: <https://identifiers.org/tair.name/{gene_model}>
- Evidence: <urn:pmw-pheno:evidence:{AGI}>
- TO term: <http://purl.obolibrary.org/obo/TO_{number}>

A gene_model can be AT3G12120.1.
Preserve leading zeros in TO numbers, e.g. 0000071.

Metabolites may use InChIKey, ChEBI, MetaNetX or PubChem URIs.
Use supplied IDs or recorded labels; do not invent identifiers.


10. QUERY CONSTRUCTION

- Use explicit GRAPH blocks and join resources by URI.
- Resolve names using recorded labels or titles.
- Use SELECT DISTINCT for unique entity lists.
- Use COUNT(DISTINCT ?gene) for gene counts.
- Do not merge distinct reaction URIs based only on similar chemistry.
- Missing data or empty results do not establish biological absence.
"""

#the complete example: english question and the correct SPARQL query.
example_query1 = """
Question: Which proteins are associated with AT3G51240?

SPARQL:
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?gene ?protein ?proteinLabel
WHERE {
    VALUES ?gene {
        <https://identifiers.org/tair.name/AT3G51240>
    }

    GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways> {
        ?gene a wp:GeneProduct .

        ?geneProteinInteraction
            a wp:TranscriptionTranslation ;
            wp:source ?gene ;
            wp:target ?protein .

        ?protein a wp:Protein .
        OPTIONAL { ?protein rdfs:label ?proteinLabel . }
    }
}
ORDER BY ?protein
"""

example_query2 = """
Question: Which TO traits are linked to the phenotype evidence of AT3G51240?

SPARQL:
PREFIX tairp: <urn:pmw-pheno:vocab:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?gene ?evidence ?trait ?traitLabel
WHERE {
    VALUES ?gene {
        <https://identifiers.org/tair.name/AT3G51240>
    }

    GRAPH <urn:pmw-pheno:graph:tair-evidence> {
        ?gene tairp:hasEvidence ?evidence .
        ?evidence a tairp:Evidence .
    }

    GRAPH <urn:pmw-pheno:graph:tair-evidence_to> {
        ?evidence tairp:hasOntologyTerm ?trait .
        ?trait a owl:Class .
        OPTIONAL { ?trait rdfs:label ?traitLabel . }
    }
}
ORDER BY ?trait
"""

example_query3 = """
Question: Show the Evidence node, TO terms, proteins, reactions, substrates and products linked to AT3G51240. Include names for TO terms, proteins and metabolites, and keep available information when a branch is missing.

SPARQL:
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX tairp: <urn:pmw-pheno:vocab:>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT
    ?gene ?evidence ?trait ?traitLabel
    ?protein ?proteinLabel ?reaction
    ?substrate ?substrateLabel ?product ?productLabel
WHERE {
    VALUES ?gene {
        <https://identifiers.org/tair.name/AT3G51240>
    }

    # Metabolic branch
    GRAPH <http://rdf-plantmetwiki.bioinformatics.nl/graph/pathways> {
        ?gene a wp:GeneProduct .

        OPTIONAL {
            ?geneProteinInteraction
                a wp:TranscriptionTranslation ;
                wp:source ?gene ;
                wp:target ?protein .

            ?protein a wp:Protein .
            OPTIONAL { ?protein rdfs:label ?proteinLabel . }

            OPTIONAL {
                ?catalysis
                    a wp:Catalysis ;
                    wp:source ?protein ;
                    wp:target ?reaction .

                ?reaction a wp:Conversion .

                OPTIONAL {
                    ?reaction wp:source ?substrate .
                    OPTIONAL {
                        ?substrate rdfs:label ?substrateLabel .
                    }
                }

                OPTIONAL {
                    ?reaction wp:target ?product .
                    OPTIONAL {
                        ?product rdfs:label ?productLabel .
                    }
                }
            }
        }
    }

    # Phenotype branch
    OPTIONAL {
        GRAPH <urn:pmw-pheno:graph:tair-evidence> {
            ?gene tairp:hasEvidence ?evidence .
            ?evidence a tairp:Evidence .
        }

        OPTIONAL {
            GRAPH <urn:pmw-pheno:graph:tair-evidence_to> {
                ?evidence tairp:hasOntologyTerm ?trait .
                ?trait a owl:Class .
                OPTIONAL { ?trait rdfs:label ?traitLabel . }
            }
        }
    }
}
ORDER BY ?trait ?protein ?reaction ?substrate ?product
"""
