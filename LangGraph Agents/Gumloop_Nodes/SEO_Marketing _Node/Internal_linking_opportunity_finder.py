import requests
import re
from bs4 import BeautifulSoup
from typing import List

# -------------
# PLACEHOLDER: Imports for your LLM (Groq + LangChain style).
# Replace these with your actual Groq + LangChain imports/interfaces.
# -------------
# Example for illustration:
#
# from langchain import PromptTemplate, LLMChain
# from langchain.chat_models import ChatOpenAI
# import groq
#
# We'll create dummy classes/variables for demonstration.


# -----------------------------------------------------------------
class DummyGroqLLM:
    pass
    # """
    # This is a placeholder class to demonstrate how you might structure
    # calls to a Groq-based LLM. Replace with your actual implementation.
    # """
    # def __init__(self, model_name: str = "groq-default", temperature: float = 0.7):
    #     self.model_name = model_name
    #     self.temperature = temperature

    # def run(self, prompt: str) -> str:
    #     # Placeholder for real inference call
    #     return f"[Simulated Groq Response for prompt:\n{prompt}\n]"


# -------------
# 1) FETCH THE SITEMAP
# -------------
def fetch_sitemap(root_domain: str) -> str:
    """
    Appends '/sitemap.xml' to the root domain, fetches the sitemap.
    Returns the raw XML string.
    """
    sitemap_url = root_domain.rstrip("/") + "/sitemap.xml"
    response = requests.get(sitemap_url)
    if response.status_code == 200:
        return response.text
    else:
        raise ValueError(f"Failed to fetch sitemap from {sitemap_url}, Status code: {response.status_code}")


# -------------
# 2) PARSE THE SITEMAP
# -------------
def parse_sitemap(sitemap_xml: str) -> List[str]:
    """
    Given the sitemap XML as a string, parse it using BeautifulSoup (xml parser).
    Return a list of URLs.
    """
    soup = BeautifulSoup(sitemap_xml, "xml")
    url_tags = soup.find_all("loc")
    links = [tag.text.strip() for tag in url_tags if tag.text]
    return links


# -------------
# 3) FILTER BLOG LINKS
# -------------
def filter_blog_links(all_links: List[str], blog_url: str) -> List[str]:
    """
    From the full list of links, keep only those that contain the given blog_url (path).
    Example: blog_url='https://example.com/blog' means we keep all links containing '/blog/' or exactly matching the domain+blog path.
    """
    return [link for link in all_links if blog_url in link and link != blog_url]


# -------------
# 4) SCRAPE THE WEBPAGE
# -------------
def scrape_webpage(url: str) -> str:
    """
    Fetches the raw HTML of the given URL.
    Returns the HTML content as a string.
    """
    resp = requests.get(url)
    if resp.status_code != 200:
        raise ValueError(f"Failed to retrieve page at {url}, status code {resp.status_code}")
    return resp.text


# -------------
# 5) EXTRACT BLOG CONTENT VIA LLM
# -------------
def extract_blog_content_via_llm(raw_html: str, llm: DummyGroqLLM) -> str:
    """
    Sends the raw HTML (scraped from the blog post) to an LLM with instructions
    to return only the blog content, ignoring sidebars, CTAs, etc.

    The prompt below is just an example; adapt as needed.
    """
    prompt = f"""SYSTEM MESSAGE:
You are a helpful content extraction assistant.

USER MESSAGE:
This is my scraped blog post. Please output JUST the blog content itself in Markdown:
Ignore menu options, CTA at the bottom, suggested posts, or any other non-blog content.

Blog post HTML:
{raw_html}
"""
    cleaned_content = llm.run(prompt)
    return cleaned_content


# -------------
# 6) CREATE INTERNAL LINKING PROMPT
# -------------
def create_internal_linking_prompt(
    blog_url: str,
    cleaned_blog_content: str,
    other_blog_posts: List[str]
) -> str:
    """
    Combines the cleaned blog content (input1), 
    the list of other blog posts (input2), 
    and the current blog URL (input3),
    into the final prompt (system + user instructions).
    """
    # Format the final user prompt
    user_prompt = f"""
You are an expert SEO consultant specializing in internal linking strategies for blogs.

Current blog post URL:
{blog_url}

Blog post content to analyze:
{cleaned_blog_content}

Available blog posts for internal linking:
{other_blog_posts}
"""

    # The system instructions / rules you provided
    system_instructions = """
SYSTEM MESSAGE (Rules/Instructions):
1. Carefully read and understand the content of the given blog post.
2. Review the list of available blog post URLs, excluding the current blog post URL.
3. Identify opportunities where the content of the given blog post naturally relates to the topics of the other available posts (based on their URLs).
4. For each relevant internal linking opportunity you identify:
   a. Provide the URL of the post to link to.
   b. Quote the exact sentence from the main blog post where the link should be inserted.
   c. Specify the exact words within that sentence that should be hyperlinked.
   d. Briefly explain why this internal link is relevant and valuable (1-2 sentences max).
5. Prioritize quality over quantity. Only suggest links that genuinely add value to the reader's experience and are contextually relevant.
6. Aim for a natural distribution of links throughout the post, avoiding over-optimization.
7. Present your suggestions in a clear, structured format for easy implementation.
8. Do not suggest linking to the current blog post URL.
9. All of the link suggestions should be EXTREMELY simple and straightforward. 
   There should be no logical leaps, it should be like Wikipedia. 
   For example, if there is mention of "United States of America", then the "United States of America" article gets linked, not "History of the United States of America".
10. Be SO selective about your linking, do not exceed 1 or 2 links per blog post, or none if not relevant.
11. The EXACT anchor text should be in the "In sentence" block.
12. The anchor text should be just a few words MAXIMUM (often 1 or 2 words).
"""

    final_prompt = system_instructions + "\nUSER MESSAGE:\n" + user_prompt
    return final_prompt


# -------------
# 7) ASK GROQ FOR LINK OPPORTUNITIES
# -------------
def ask_groq_for_link_opportunities(final_prompt: str, llm: DummyGroqLLM) -> str:
    """
    Calls the LLM with the final combined system + user prompt to obtain
    the internal linking recommendations.
    Returns the raw LLM response (which should be a structured set of suggestions).
    """
    result = llm.run(final_prompt)
    return result


# -------------
# 8) MAIN ORCHESTRATION
# -------------
def internal_linking_opportunity_finder(root_domain: str, blog_url: str) -> str:
    """
    Orchestrates:
    1. Fetch sitemap
    2. Parse to get all links
    3. Filter blog links
    4. Scrape the targeted blog_url to get raw HTML
    5. Clean the blog content via an LLM
    6. Use the rest of blog links (excluding current blog post) to create final prompt
    7. Send prompt to LLM for internal link suggestions
    8. Return the LLM's response
    """
    # Initialize your LLM (Groq or otherwise)
    groq_llm = DummyGroqLLM(model_name="groq-default", temperature=0.7)

    # 1) Fetch and parse sitemap
    sitemap_xml = fetch_sitemap(root_domain)
    all_links = parse_sitemap(sitemap_xml)

    # 2) Filter blog links from all links
    filtered_blog_links = filter_blog_links(all_links, blog_url)

    # 3) Scrape the main blog_url for raw HTML
    raw_html = scrape_webpage(blog_url)

    # 4) Clean the content with an LLM prompt
    cleaned_content = extract_blog_content_via_llm(raw_html, groq_llm)

    # 5) Create the final prompt to find linking opportunities
    final_prompt = create_internal_linking_prompt(
        blog_url=blog_url,
        cleaned_blog_content=cleaned_content,
        other_blog_posts=filtered_blog_links
    )

    # 6) Ask LLM for link opportunities
    link_opportunities = ask_groq_for_link_opportunities(final_prompt, groq_llm)

    return link_opportunities


# -------------
# USAGE EXAMPLE (replace with real domain and blog URL)
# -------------
if __name__ == "__main__":
    root = "https://example.com"
    blog = "https://example.com/blog/my-latest-post"
    
    suggestions = internal_linking_opportunity_finder(root, blog)
    print("Internal Linking Suggestions:\n", suggestions)
