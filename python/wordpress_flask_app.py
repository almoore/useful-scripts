from flask import Flask, redirect, request, url_for
import requests
import os

app = Flask(__name__)

CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:8000/callback'

@app.route('/')
def home():
    authorization_url = (
        f"https://public-api.wordpress.com/oauth2/authorize?"
        f"client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code"
    )
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    authorization_code = request.args.get('code')
    if authorization_code:
        token_url = "https://public-api.wordpress.com/oauth2/token"
        data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI,
            'code': authorization_code,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            access_token = response.json().get('access_token')
            return f"ACCESS_TOKEN={access_token}"
        else:
            return f"Failed to obtain access token: {response.status_code} {response.text}"
    return "No code found in request."

if __name__ == '__main__':
    app.run(port=8000)
