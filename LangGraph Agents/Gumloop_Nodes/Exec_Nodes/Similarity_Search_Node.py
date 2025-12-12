from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain.docstore.document import Document
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.vectorstores import FAISS
from typing import List

def similarity_search(query: str, text: str, chunk_size: int = 100, chunk_overlap: int = 100, search_type: str = "similarity", k: int = 5) -> List[str]:
    """
    Perform a similarity search through a large text to retrieve relevant sections based on the query.

    Args:
        query (str): The search query or term to find in the large text.
        text (str): The large body of text to search through.
        chunk_size (int): The size of each text chunk. Default is 900 tokens (roughly corresponding to words).
        search_type (str): Type of search to use ('similarity_search' or 'mmr'). Default is 'similarity_search'.
        k (int): The number of top documents to return. Default is 5.
        
    Returns:
        List[str]: A list of text chunks most relevant to the search query.
    """
    
    # Step 1: Split the text into chunks using RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(separators=['\n\n'], chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    splits = text_splitter.split_text(text)
    
    # Step 2: Convert each chunk into a Document object
    documents = [Document(page_content=chunk) for chunk in splits]

    # Step 3: Set up HuggingFaceBgeEmbeddings for creating vector embeddings
    model_name = "BAAI/bge-small-en"
    model_kwargs = {"device": "cpu"}
    encode_kwargs = {"normalize_embeddings": True}
    hf_embeddings = HuggingFaceBgeEmbeddings(
        model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs
    )

    # Step 4: Create a FAISS vector store with the embeddings of the documents
    vectorstore = FAISS.from_documents(documents=documents, embedding=hf_embeddings)

    # Step 5: Set up the retriever with search type
    retriever = vectorstore.as_retriever(search_type=search_type, search_kwargs={"k": k})

    # Step 6: Retrieve the most relevant documents based on the query
    related_docs = retriever.invoke(query)
    
    # Return the top 'k' relevant chunks
    return related_docs

# query = "What are the benefits of AI?"
# text = """AI is transforming industries. AI can help healthcare with data analysis. AI also benefits automation..."""
# results = similarity_search(query, text, chunk_size=100,chunk_overlap=0, search_type="similarity", k=1)
# print(results)