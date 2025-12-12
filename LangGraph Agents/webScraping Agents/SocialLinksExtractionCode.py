from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
import csv

# Function to set up the browser
def setup_browser(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    return driver

# Function to extract links from Google search results (only first page)
def extract_links_from_google(query, headless=True):
    driver = setup_browser(headless=headless)
    urls = [] 
    try:
        driver.get("https://www.google.com")
        time.sleep(3)
        
        search_box = driver.find_element(By.NAME, "q")
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
        time.sleep(60) 
        
        # Extract links from first page
        results = driver.find_elements(By.CSS_SELECTOR, "div.tF2Cxc")
        for result in results:
            try:
                title = result.find_element(By.CSS_SELECTOR, "h3").text
                url = result.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                urls.append({"query": query, "title": title, "url": url})
            except Exception as e:
                print(f"Error extracting link: {e}")
    finally:
        driver.quit()
    return urls

# Function to save links to CSV
def save_to_csv(data, filename):
    keys = ["query", "title", "url"]
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

# Main Function
if __name__ == "__main__":
    base_query = "site:linkedin.com/in/ (top 10 Seed Investor) Texas"
    suffixes = ["LinkedIn", "Instagram", "YouTube", "Twitter", "GitHub"]
    
    all_links = []

    for suffix in suffixes:
        query = f"{base_query} {suffix}"
        print(f"Extracting links for: {query}")
        links = extract_links_from_google(query, headless=False)  # Set to True for headless mode
        all_links.extend(links)

    save_to_csv(all_links, "social_media_profiles.csv")
    print(f"Saved {len(all_links)} links to 'social_media_profiles.csv'.")
