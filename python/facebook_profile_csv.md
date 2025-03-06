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


The Facebook Graph API provides access to a variety of fields, depending on the object you're querying and the permissions you've obtained. Here's a general overview of the types of fields you can access for a user object, given the appropriate permissions:

### Basic Profile Information
- **id**: The user's unique ID on Facebook.
- **name**: The user's full name.
- **first_name**: The user's first name.
- **last_name**: The user's last name.
- **short_name**: The user's abbreviated name.

### Contact Information (with appropriate permissions)
- **email**: The user's primary email address (requires the `email` permission).

### Personal Details (with appropriate permissions)
- **birthday**: The user's birthday (requires the `user_birthday` permission).
- **gender**: The user's gender.
- **hometown**: The user's hometown details (requires the `user_hometown` permission).
- **location**: The user's current city (requires the `user_location` permission).
- **languages**: The languages that the user speaks.

### Work and Education (with appropriate permissions)
- **education**: Information about the user's education history.
- **work**: Information about the user's work history.

### Relationships and Family (with appropriate permissions)
- **relationship_status**: The user's relationship status.
- **significant_other**: Information about the user's significant other.

### Likes and Interests (with appropriate permissions)
- **likes**: Pages that the user has liked.

### Events and Groups (with appropriate permissions)
- **events**: Events that the user is attending or invited to.
- **groups**: Groups the user is a member of.

### Photos and Videos (with appropriate permissions)
- **photos**: Photos uploaded by the user.
- **videos**: Videos uploaded by the user.

### Posts and Content (with appropriate permissions)
- **posts**: The user's posts.
- **feed**: The user's News Feed.

### Security and Privacy Considerations
- Always respect user privacy and ensure that your application complies with Facebook's Data Policy and terms of service.
- Only request permissions that are necessary for your application's functionality.
- Handle user data responsibly and securely.

### Using the Graph API
When querying the Graph API, you can specify which fields you're interested in using the `fields` parameter. For example, to get a user's name, email, and birthday, your Graph API request URL might look like this:

```plaintext
https://graph.facebook.com/v11.0/me?fields=id,name,email,birthday&access_token=YOUR_ACCESS_TOKEN
```

Remember that accessing certain fields requires specific permissions from the user, and some fields may not be available depending on the user's privacy settings. Always test your application with the necessary permissions to ensure it works as expected.
