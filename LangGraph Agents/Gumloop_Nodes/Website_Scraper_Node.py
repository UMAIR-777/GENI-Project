import requests
from bs4 import BeautifulSoup

def website_scraper_node(url):
    '''
    Description:
    This function takes in the URL of a website and does the following:
    -> Extracts all the content of the target website 

    Args: Website URL (https://www.example.com/)

    '''
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        all_text = soup.get_text(separator=' ')  
        cleaned_text = ' '.join(all_text.split())  
        return cleaned_text
    else:
        return f"Failed to retrieve the website. Status code: {response.status_code}"
