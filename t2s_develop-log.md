# Text-to-SPARQL
This file tracks the step-by-step development of the text-to-SPARQL function for plantmetwiki

2026-09-16: combined the graph-viz server and the new translate feature (t2s-server) into
one Flask app and port 5000
Add textbox for English question input and connect the python server to the interface,
whatever input in the textbox and it will return as it is.

Next: parse the incoming text for exactly one TAIR gene ID or
UniProt accession. connect the t2s_server with GPT API.