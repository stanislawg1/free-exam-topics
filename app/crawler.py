import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .filter import filter_discussion_links

def _page_exists(url, headers, exam_provider, page_number):
    url = f"{url}/discussions/{exam_provider}/{page_number}"
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return True
        elif r.status_code == 429:
            raise LookupError("_page_exists 429 error")
        else:
            return False
    except Exception as e:
        print(e)
        print(r.status_code)
        return False

def find_max_page(url, headers, exam_provider, start_upper=10_000):
    low = 1
    high = start_upper

    max_found = 0

    while low <= high:
        mid = (low + high) // 2
        if _page_exists(url, headers, exam_provider, mid):
            max_found = mid
            low = mid + 1
        else:
            high = mid - 1

    return max_found

def get_links_from_page(url, headers):

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    links = set()

    for a in soup.find_all("a", href=True):
        link = urljoin(url, a["href"])
        link = link.split("#")[0]
        links.add(link)

    return list(links)

def crawl_discussion_links(url, headers, exam_provider, page):
    links = get_links_from_page(f'{url}/discussions/{exam_provider}/{page}', headers=headers)
    return filter_discussion_links(links)
