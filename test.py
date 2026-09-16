import requests
response = requests.post("http://localhost:5000/translate", json={"gene1": "AT5G52810"}) #requests.post(...) send a POST request to the address
print(response.status_code)
print(response.text)