import autogen
import json
from dotenv import load_dotenv
import os
from tenacity import retry, wait_random_exponential, stop_after_attempt
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.identity import AzureCliCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from azure.search.documents.indexes.models import (
    SimpleField,
    SearchFieldDataType,
    SearchableField,
    SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    SearchIndex,
    AzureOpenAIVectorizer,
    AzureOpenAIParameters
)

load_dotenv()
AZURE_OPENAI_ENDPOINT=os.getenv("AISTUDIO_AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_GPT4o_DEPLOYMENT=os.getenv("AI_STUDIO_AZURE_OPENAI_GPT4o_DEPLOYMENT")
AZURE_OPENAI_API_VERSION="2024-02-01"
AZURE_OPENAI_KEY=os.getenv("AISTUDIO_AZURE_OPENAI_KEY")
OPENAI_ADA_EMBEDDING_DEPLOYMENT_NAME = os.getenv("OPENAI_ADA_EMBEDDING_DEPLOYMENT_NAME")

AZURE_SEARCH_SERVICE_ENDPOINT=os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_ADMIN_KEY=os.getenv("AZURE_SEARCH_ADMIN_KEY")
AZURE_SEARCH_INDEX=os.getenv("AZURE_SEARCH_INDEX")
AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG = os.getenv("AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG")

# Configure OpenAI API
aoai_client = AzureOpenAI(
  azure_endpoint = AZURE_OPENAI_GPT4o_DEPLOYMENT, 
  api_key=AZURE_OPENAI_KEY,  
  api_version=AZURE_OPENAI_API_VERSION
)

llm_config = {
    "cache_seed": 43,  # change the cache_seed for different trials
    "temperature": 0,
    "timeout": 120,  # in seconds
    "config_list": 
    [
        {
            "model": AZURE_OPENAI_GPT4o_DEPLOYMENT,
            "api_type": "azure",
            "api_key": AZURE_OPENAI_KEY,
            "base_url": AZURE_OPENAI_ENDPOINT,
            "api_version": AZURE_OPENAI_API_VERSION
        }
    ]
}

aia_search_client = None

def config_search():
    service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
    index_name = "product_data_csv"
    credential = AzureKeyCredential(key)
    return SearchClient(endpoint=service_endpoint, index_name=index_name, credential=credential)

# Generate Document Embeddings using OpenAI Ada Model
@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
# Function to generate embeddings for title and content fields, also used for query embeddings
def calc_embeddings(text):
    # model = "deployment_name"
    embeddings = aoai_client.embeddings.create(input = [text], model=OPENAI_ADA_EMBEDDING_DEPLOYMENT_NAME).data[0].embedding
    return embeddings

# Define your tool function `search` that will interact with the Azure Cognitive Search service.
def search(query: str):
    fields = ["name", "description"]
    embedding = calc_embeddings(query)
    vector_query = VectorizedQuery(vector=embedding, k_nearest_neighbors=3, fields=fields)
  
    results = aia_search_client.search(  
        search_text=None,  
        vector_queries= [vector_query],
        select=["name", "description"],
    )  


    output = []
    for result in results:
        result.pop("titleVector")
        result.pop("contentVector")
        output.append(result)

    return output


def define_agents():
    user_proxy = autogen.UserProxyAgent(
        name="Admin",
        system_message="A human admin. Interact with the WebSearchEngineer and AzureAISearcher and decides who to assign the task to.",
        code_execution_config={
            "work_dir": "code",
            "use_docker": False
        },
        human_input_mode="TERMINATE",
    )

    web_search_engineer = autogen.AssistantAgent(
        name="WebSearchEngineer",
        llm_config=llm_config,
        system_message="""Engineer. You follow an approved plan. Make sure you save code to disk.  You write python/shell 
        code to solve tasks. Wrap the code in a code block that specifies the script type and the name of the file to 
        save to disk.""",
    )

    aia_searcher = autogen.AssistantAgent(
        name="AzureAISearcher",
        llm_config=llm_config,
        system_message="You are a helpful AI assistant that answers questions about the electronics product catalog only. "
        "You can help with Azure AI Search on the electronics product catalog."
        "Return 'TERMINATE' when the task is done.",
    )
    group_chat = autogen.GroupChat(
        agents=[user_proxy, web_search_engineer, aia_searcher], messages=[], max_round=12
    )

    manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=llm_config)
    return manager, user_proxy, web_search_engineer, aia_searcher


if __name__ == "__main__":
    aia_search_client = config_search()
    manager, user_proxy, web_search_engineer, aia_searcher = define_agents()

    user_proxy.initiate_chat(
        manager,
        message="""
            Find all the products with the word 'laptop' in the description.
        """,
    )