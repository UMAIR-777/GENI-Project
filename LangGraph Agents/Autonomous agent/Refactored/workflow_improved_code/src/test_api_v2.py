import requests
from typing import List

def embed_texts(
    texts: List[str],
    api_url: str = "https://bge-m3-v1-998052755917.us-central1.run.app/embed",
) -> List[List[float]]:
    """
    Send a list of strings to your embedding API and return the dense vectors.
    
    Args:
      texts: The input sentences to embed.
      api_url: Full URL of your /embed endpoint.

    Returns:
      A list of embedding vectors (one list of floats per input string).
    """
    payload = {"texts": texts}
    resp = requests.post(api_url, json=payload)
    resp.raise_for_status()              # will raise an error for non-2xx
    data = resp.json()
    return data["dense_vecs"]

if __name__ == "__main__":
    sample = ["hello", "world"]
    embs = embed_texts(sample)
    print(embs)
    print(type(embs))
    print(len(embs))
    print(len(embs[0]))
