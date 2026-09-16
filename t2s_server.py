from flask import request
import requests
from GV_server import app

@app.route('/translate', methods=['POST'])
def testing(): #you need to return sth, not just print()
    response = request.get_json()

    return response, 'hello'

if __name__ == '__main__':
    app.run(port=5000)