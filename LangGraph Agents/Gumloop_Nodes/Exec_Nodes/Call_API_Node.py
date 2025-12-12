import requests
from typing import Optional, Dict, Any

def call_api(method: str, url: str, headers: Optional[Dict[str, str]] = None, body: Optional[Dict[str, Any]] = None) -> str:
    """
    Makes an HTTP request to the given URL using the specified method, headers, and body.

    Args:
        method (str): The HTTP method ('GET' or 'POST').
        url (str): The destination URL for the API request.
        headers (Optional[Dict[str, str]]): Optional headers to send with the request.
        body (Optional[Dict[str, Any]]): Optional body data to send with the request (for POST).

    Returns:
        str: The raw response from the API request, typically in JSON format or plain text.
    """
    if method.upper() == 'GET':
        response = requests.get(url, headers=headers)
    elif method.upper() == 'POST':
        response = requests.post(url, headers=headers, json=body)
    else:
        raise ValueError("Invalid HTTP method. Supported methods are 'GET' and 'POST'.")

    return response.text

# response = call_api('GET', 'https://cat-fact.herokuapp.com/facts/')
# print(response)

