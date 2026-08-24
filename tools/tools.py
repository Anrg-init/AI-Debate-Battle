from dotenv import load_dotenv
load_dotenv
from langchain_tavily import TavilySearch


# travily tool calling
search_tool = TavilySearch(max_results=2)



