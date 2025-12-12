import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

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
    links = []  
    try:
        driver.get("https://www.google.com")
        time.sleep(3)
        
        search_box = driver.find_element(By.NAME, "q")
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
        time.sleep(60)  # Allow time for results to load
        
        # Extract links from first page
        results = driver.find_elements(By.CSS_SELECTOR, "div.tF2Cxc")
        for result in results[:5]:  # Limiting to top 5 results for each search
            try:
                url = result.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                links.append(url)
            except Exception as e:
                print(f"Error extracting link: {e}")
    finally:
        driver.quit()
    
    return links

def process_csv(input_csv, output_csv, suffixes):
    with open(input_csv, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        data = list(reader)  

    output_data = []

    for row in data:
        title = row["title"]
        new_row = {"title": title}  
        for suffix in suffixes:
            query = f"{title} {suffix}"
            print(f"Searching for: {query}")
            links = extract_links_from_google(query, headless=False)  # Change to True for headless mode
            
            for i, link in enumerate(links):
                new_row[f"link{i+1}"] = link

        output_data.append(new_row)
        save_to_csv(output_data, output_csv)

# Function to save links to CSV
def save_to_csv(data, filename):
    keys = ["title"] + [f"link{i+1}" for i in range(10)]  
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

# Main Execution
if __name__ == "__main__":
    input_csv = "social_media_profiles.csv"  
    output_csv = "texas_extracted_links.csv"
    suffixes = ["Instagram", "LinkedIn", "Twitter (X)", "GitHub", "TikTok", "Facebook"]

    process_csv(input_csv, output_csv, suffixes)
    print(f"Data extraction completed! Results saved in '{output_csv}'.")
