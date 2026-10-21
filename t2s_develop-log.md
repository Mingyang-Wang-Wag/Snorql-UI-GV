# Text-to-SPARQL
This file tracks the step-by-step development of the text-to-SPARQL function for plantmetwiki

2026-09-16: combined the graph-viz server and the new translate feature (t2s-server) into
one Flask app and port 5000
Add textbox for English question input and connect the python server to the interface,
whatever input in the textbox and it will return as it is.

Next: parse the incoming text for exactly one TAIR gene ID or
UniProt accession. connect the t2s_server with GPT API.

2026-09-17: wired GPT-5 into /translate - loads the key from .env, prompt
text lives in prompt.py, returns the generated query plus token counts
and response time (found most tokens are hidden "reasoning" tokens, not
the visible answer). Generated query now fills into the existing SPARQL
box via script.js instead of auto-running on the server.

To-do:
- find the real gene URI format (current guesses return 0 results)
- add the gene-anchored example once confirmed
- log generated queries somewhere for later evaluation
