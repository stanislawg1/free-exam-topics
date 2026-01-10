import requests
from bs4 import BeautifulSoup


def get_all_providers(base_url: str, headers: dict):
    response = requests.get(f"{base_url}/exams/", headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    result = {}

    for a in soup.select("a[href*='/exams/']"):
        href = a["href"].strip("/")
        slug = href.split("/")[-1]
        name = a.get_text(strip=True).split("(")[0].strip()
        
        if slug not in result:
            result[slug] = name

    return result



def get_provider_exams(base_url: str, headers: dict, provider_name):
    response = None

    try:
        response = requests.get(f"{base_url}/exams/{provider_name}", headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(e)
    
    soup = BeautifulSoup(response.text, "html.parser")

    result = {}

    for a in soup.select("a.popular-exam-link"):
        full_text = a.text.strip()
        href = a["href"]
        simple_name = href.rstrip("/").split("/")[-1]
        result[simple_name] = full_text

    return result
