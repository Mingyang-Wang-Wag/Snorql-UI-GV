import requests
response = requests.post("http://localhost:5000/translate", json="Show me the info about AT5G40390") #send a POST request to the address
print(response.text)



#AT5G40390 and Q9FND9