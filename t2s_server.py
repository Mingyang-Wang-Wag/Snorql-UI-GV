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
from prompt import system_prompt, schema_prompt, example_query1, example_query2, example_query3

#setting
endpoint_pmw = "https://plantmetwiki.bioinformatics.nl/sparql"
endpoint_local = "http://localhost:8890/sparql"
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key = api_key)


@app.route('/translate', methods=['POST']) #get /evidence and /graph from GV_server.py, add /translate here.
def main():
    """
    Sending the user's question to gpt API and capture the response. return the response and some evaluation parameters

    """
    server_response = request.get_json()
    user_question = server_response

    start = time.time()
    gpt_response = client.chat.completions.create(model="gpt-6-astra", messages=[{'role': 'user','content':
        f'{system_prompt} {schema_prompt} {example_query1} {example_query2} {example_query3}. Generate a SPARQL query given this question {user_question}.'}])
    end = time.time()
    elapsed = end - start

    print("Prompt tokens:", gpt_response.usage.prompt_tokens)
    print("Completion tokens:", gpt_response.usage.completion_tokens) #tokens of generated SPARQL query and tokens of inference to generate
    print("Total tokens:", gpt_response.usage.total_tokens)
    print("Response time (seconds):", elapsed)

    usage = gpt_response.usage
    details = usage.prompt_tokens_details

    cached = getattr(details, "cached_tokens", 0) or 0
    written = getattr(details, "cache_write_tokens", 0) or 0
    ordinary = usage.prompt_tokens - cached - written

    cost = (
        ordinary * 10
        + cached * 1
        + written * 12.5
        + usage.completion_tokens * 50
    ) / 1_000_000 #the cost of token is categorized into three groups, cached, written, usage

    print(f"Estimated cost (USD): ${cost:.5f}")

    return {"query":gpt_response.choices[0].message.content}

if __name__ == '__main__':
    app.run(port=5000)


