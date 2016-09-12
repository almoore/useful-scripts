import requests

url = "https://www.facebook.com/dialog/oauth"

headers = {
    'client_id': "1008216755952076",
    'cache-control': "no-cache",
    'postman-token': "de5313b9-1dea-d507-8e8e-3898db1b0c19"
    }

response = requests.request("GET", url, headers=headers)

print(response.text)
