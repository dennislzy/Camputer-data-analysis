import os
from langchain_openai import ChatOpenAI
import requests


def  generate_category():
    url = "http://localhost:8080/api/camp-categories/distinct-categories"
    response = requests.get(url)
    try:
        return response.json()
    except ValueError:
        print("無法解析 JSON 響應")
        return response.text




