# -*- coding: utf-8 -*-
"""Gen.Ai final.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1X3zErK9gkimbeqpDmWvh4PTbMQbWg0uJ
"""

!pip install sentence-transformers==2.4.0
!pip install python-dotenv
!pip install pinecone[grpc]
!pip install langchain-pinecone
!pip install langchain_community
!pip install langchain-groq
!pip install langchain_experimental
!pip install langchain-core
!pip install pinecone
!pip install tiktoken beautifulsoup4 requests jina

import pandas as pd
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_pinecone import PineconeVectorStore
from typing import Optional
from bs4 import BeautifulSoup
import requests

# ✅ 2. Import Libraries
import pandas as pd
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional, Dict

# ✅ 3. Scraping Function with Jina AI + BeautifulSoup fallback
def fetch_url_content(domain: str) -> Optional[Dict]:
    prefix_url = "https://r.jina.ai/"
    full_url = prefix_url + domain
    timestamp = datetime.utcnow().isoformat()

    try:
        response = requests.get(full_url, timeout=15)
        if response.status_code == 200:
            print(f"[Jina AI] ✅ {domain}")
            return {"domain": domain, "content": response.text, "timestamp": timestamp}
        else:
            print(f"[Jina AI] ❌ {domain} | Status: {response.status_code}")
    except requests.RequestException as e:
        print(f"[Jina AI] ⚠️ {domain} | Exception: {e}")

    # Fallback to BeautifulSoup
    try:
        print(f"[Fallback] Trying BeautifulSoup for {domain}")
        response = requests.get("https://" + domain, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            return {"domain": domain, "content": text, "timestamp": timestamp}
        else:
            print(f"[BeautifulSoup] ❌ {domain} | Status: {response.status_code}")
    except requests.RequestException as e:
        print(f"[BeautifulSoup] ⚠️ {domain} | Exception: {e}")

    return None

# ✅ 4. Scrape New Domains (live)
live_domains = ["openai.com", "huggingface.co"]  # Replace or extend dynamically
scraped_results = []

for domain in live_domains:
    result = fetch_url_content(domain)
    if result:
        scraped_results.append(result)

# ✅ 5. Load Existing Labeled Dataset
labeled_data = pd.read_csv("Genai and not gen ai data.csv")
labeled_data.columns = ['domain', 'label']
labeled_data['domain'] = labeled_data['domain'].str.strip()
labeled_data['label'] = labeled_data['label'].str.strip()

# ✅ 6. Convert Everything into LangChain Document Objects
# Labeled DB Data
db_documents = [
    Document(page_content=row['domain'], metadata={"label": row['label']})
    for _, row in labeled_data.iterrows()
]

# Live Scraped Content
scraped_documents = [
    Document(
        page_content=item["content"],
        metadata={"domain": item["domain"], "timestamp": item["timestamp"]}
    )
    for item in scraped_results
]

# Combine both sources
all_documents = db_documents + scraped_documents
print(f"\n✅ Total Combined Documents: {len(all_documents)}")

# ✅ 7. Chunking Function
def text_split(docs):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    return text_splitter.split_documents(docs)

text_chunks = text_split(all_documents)
print(f"✅ Total Text Chunks: {len(text_chunks)}")

# ✅ 8. Optional Preview
for i in range(min(3, len(text_chunks))):
    print(f"\n🔹 Chunk {i + 1}:\n{text_chunks[i].page_content[:500]}")

# ⏭️ Next:
# - Embed text_chunks using Hugging Face
# - Store into Pinecone
# - Run classification via Groq or OpenAI

def download_hugging_face_embeddings():
    embeddings=HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
    return embeddings

embeddings = download_hugging_face_embeddings()

query_result = embeddings.embed_query("Hello world")
print("Length", len(query_result))

from google.colab import files
files.upload()

from dotenv import load_dotenv
load_dotenv('.env')

import os
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
import os

pc = Pinecone(api_key=PINECONE_API_KEY)

index_name = "my-domain-bot"


pc.create_index(
    name=index_name,
    dimension=384,
    metric="cosine",
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"
    )
)

from pinecone import Pinecone

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

from langchain_pinecone import PineconeVectorStore

docsearch = PineconeVectorStore.from_documents(
    documents=text_chunks,
    index_name=index_name,
    embedding=embeddings,
)

from langchain_pinecone import PineconeVectorStore
# Embed each chunk and upsert the embeddings into your Pinecone index.
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)

docsearch

retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k":3})

retrieved_docs = retriever.invoke("generative ai")

retrieved_docs

from langchain_groq import ChatGroq

llm = ChatGroq(
        temperature=0,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        #model_name="llama-3.3-70b-versatile"
        model_name="llama-3.1-8b-instant"
    )

from langchain.prompts import ChatPromptTemplate

# Define the system prompt
system_prompt = """
1. **Generative AI**:
   - The site uses AI to generate visible content such as text, images, audio, video, code, insights, etc.
   - Phrases like: “generate content,” “create music,” “AI writer,” “text-to-speech,” or anything about creating content are strong indicators.

2. **Not Generative AI**:
   - The site uses AI only for automation, analytics, optimization, or personalization.
   - No visible creative content is generated for the end user.

Use the scraped text from the website and compare it with similar examples retrieved from the vector database. Use that context to make a confident decision.

**Your output should be in this format**:
- Domain: [e.g., novelai.tech]
- Classification: [Generative AI / Not Generative AI]
- Reason: [Short, clear explanation based on observed text or retrieved examples]

Only choose from the two labels: "Generative AI" or "Not Generative AI".
"""

# Construct the prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "Domain: {input}\n\nContext:\n{context}")
])

question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

domain_name = "chatgpt.com"
result = rag_chain.invoke({"input": domain_name})
print("Prediction:", result["answer"])

domain_name = "wikipedia.org/"
result = rag_chain.invoke({"input": domain_name})
print("Prediction:", result["answer"])

domain_name = "aiforeducation.io"
result = rag_chain.invoke({"input": domain_name})
print("Prediction:", result["answer"])

domain_name = "brainlogic.ai"
result = rag_chain.invoke({"input": domain_name})
print("Prediction:", result["answer"])

domain_name = "usestackaiapp.com"
result = rag_chain.invoke({"input": domain_name})
print("Prediction:", result["answer"])

import pandas as pd

df = pd.read_csv("www.csv") # Must have a 'domain' column
df["prediction"] = df["domain names"].apply(lambda x: rag_chain.invoke({"input": x})["answer"])
df.to_csv("classified_domains.csv", index=False)

df = pd.read_csv("classified_domainss.csv", encoding='ISO-8859-1')
print(df.head())         # Preview the first 5 rows
print(df.columns)        # Show the column names

# Start by cleaning and parsing the 'prediction' column
def extract_info(row):
    try:
        parts = row.split('\n')
        domain = parts[0].split(':', 1)[1].strip()
        classification = parts[1].split(':', 1)[1].strip()
        reason = parts[2].split(':', 1)[1].strip()
        return pd.Series([domain, classification, reason])
    except Exception as e:
        return pd.Series([None, None, None])  # Handle unexpected format

# Apply the function to your DataFrame
df[['domain', 'classification', 'reason']] = df['prediction'].apply(extract_info)

# Optional: drop the old prediction column and keep the clean result
df_cleaned = df[['domain', 'classification', 'reason']]
print(df_cleaned.head())

# Assuming your cleaned DataFrame is named `final_df`
df_cleaned.to_csv("classified_domains.csv", index=False)

!git config --global user.email "directbookstoreltd@gmail.com"
!git config --global user.name "Directbookstore"

!git clone https://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@github.com/Directbookstore/Domain-Classification.git

# Commented out IPython magic to ensure Python compatibility.
# %cd Domain-Classification

!git add .
!git commit -m "Add Gen.Ai final notebook"
!git push origin main

ls /content/Domain-Classification