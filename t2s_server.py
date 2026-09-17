#server imports
from flask import request
import requests

import requests
from GV_server import app

#GPT import
import os
from dotenv import load_dotenv
from openai import OpenAI

#testing import
import re
import time

#prompt import
from prompt import system_prompt, schema_prompt, query_prompt_protein, query_prompt_gene


endpoint = "https://plantmetwiki.bioinformatics.nl/sparql"

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key = api_key)



@app.route('/translate', methods=['POST'])
def tair_uniprot_parser():
    """
    Extract the TAIR or the UniProt id in the user's input Enlgish question
    put it together with prompt and send to GPT-5

    """

    server_response = request.get_json()
    question = server_response

    tair_pattern = r"AT[1-5CM]G\d{5}"
    uniprot_pattern = r"[OPQ]\d[A-Z0-9]{3}\d" # only for O/P/Q-starting form, not the other UniProt accession shape or the longer 10-character varian

    tair_id_ls = re.findall(tair_pattern, question)
    uniprot_id_ls = re.findall(uniprot_pattern, question)
    extracted_id_ls = tair_id_ls + uniprot_id_ls

    if len(extracted_id_ls) == 0:
        return f'no id was found in the: {server_response}'
    elif len(extracted_id_ls) == 1:

        start = time.time()
        gpt_response = client.chat.completions.create(model='gpt-5', messages=[{'role': 'user','content':
            f'{system_prompt} {schema_prompt} {query_prompt_gene} Generate a SPARQL query given this {extracted_id_ls[0]}.'}])
        end = time.time()
        elapsed = end - start


        return {"query":gpt_response.choices[0].message.content,
                "prompt_tokens":gpt_response.usage.prompt_tokens,
                "completion_tokens":gpt_response.usage.completion_tokens,
                "total_tokens":gpt_response.usage.total_tokens,
                "response_time": elapsed}

    elif len(extracted_id_ls) >= 2:
        return f'too much valid input: {extracted_id_ls}'


if __name__ == '__main__':
    app.run(port=5000)



'''
        pmw_response = requests.get(
            endpoint,
            params={
                "query": gpt_response.choices[0].message.content,
                "format": "application/sparql-results+json"
            }
        )
'''