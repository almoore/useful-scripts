#!/usr/bin/env python3

'''
## Requirements
1. **Facebook Developer Account:** Set up a developer account and create an app to obtain your App ID and Secret Key.
2. **Access Token:** Generate a user access token with the necessary permissions to access your profile data.
3. **Python Environment:** Ensure you have Python installed along with the requests and pandas libraries.

```
pip install requests pandas
```

To obtain a Facebook access token for the script, you'll need to follow these steps:

### 1. **Create a Facebook Developer Account and App**

1. **Sign Up**: Go to the [Facebook for Developers](https://developers.facebook.com/) site and sign up for a developer account if you don't have one.
   
2. **Create an App**: In the Facebook Developer Dashboard, click on "My Apps" and create a new app:
   - Choose the "Create App" option.
   - Follow the prompts to name your app and select the type that best fits your usage. You can choose "For Everything Else" if it's just a personal project.
   - Once the app is created, you'll receive an App ID and an App Secret.

### 2. **Generate a User Access Token**

1. **Access the Graph API Explorer**:
   - Navigate to the [Graph API Explorer](https://developers.facebook.com/tools/explorer/).
   - Select the app you've created from the "Application" dropdown menu at the top right.

2. **Get the Access Token**:
   - Click on the "Get Token" button and choose "Get User Access Token."
   - In the list of permissions, select the required permissions (e.g., `email`, `public_profile`, `user_birthday`, `user_location`) depending on the data you want to access. 

3. **Generate Token**:
   - After selecting the necessary permissions, click on "Generate Access Token."
   - Grant any permissions prompts that appear in a new window. This process will log you into Facebook and authorize the token request.

### 3. **Use the Access Token**

- After completing the steps, copy the generated access token and use it in your script by replacing `ACCESS_TOKEN = 'YOUR_ACCESS_TOKEN'` with the actual token.

### 4. **Handling Access Tokens**

- **Short-lived Tokens**: Tokens generated through the Graph API Explorer are short-lived (usually valid for about an hour). For longer testing, you may need to generate a long-lived token.
- **Long-lived Tokens**: You can exchange a short-lived token for a long-lived one using the Facebook API, but it requires additional steps and API calls.
- **Token Expiry**: Always check token expiration and re-authenticate if needed.
  
### Security Notes:

- **Never Hardcode**: Avoid hardcoding sensitive information like your access token in public repositories or shared environments.
- **Environment Variables**: Consider using environment variables or secure storage solutions to manage your tokens in production environments.

By following these steps, you'll be able to generate a Facebook access token to use in your script for data retrieval using the Graph API. Remember to comply with Facebook's terms, policies, and privacy guidelines while using the API.

'''

import requests
import pandas as pd
import json

# Replace with your own access token
ACCESS_TOKEN = 'YOUR_ACCESS_TOKEN'
BASE_URL = 'https://graph.facebook.com/v11.0/me'

def fetch_facebook_profile_data(access_token, fields=None):
    """Fetches profile data from Facebook."""
    params = {
        'access_token': access_token,
    }
    if fields:
        params['fields'] = ','.join(fields)

    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error fetching data: {response.status_code} {response.text}")

def export_to_csv(data, csv_file='facebook_profile_data.csv'):
    """Exports the fetched data to a CSV file."""
    if not data:
        print("No data to export.")
        return
    
    if isinstance(data, dict):
        data = [data]
    
    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False)
    print(f"Data exported to {csv_file}")

def main():
    # Define the fields you want to retrieve
    fields = ['id', 'name', 'email', 'birthday', 'location']  # modify according to permissions granted

    try:
        profile_data = fetch_facebook_profile_data(ACCESS_TOKEN, fields)
        print(json.dumps(profile_data, indent=2))
        export_to_csv(profile_data)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
