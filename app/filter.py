import re
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

def _extract_exam_id(url: str) -> str | None:
    path = urlparse(url).path.lower()
    
    m = re.search(r"exam-([a-z0-9\-_.]+)", path)

    return m.group(1) if m else None

def _extract_provider(url: str) -> str | None:
    path = urlparse(url).path.lower()
    parts = path.split("/")
    if "view" in parts:
        i = parts.index("view")
        if i > 0:
            return parts[i-1]
    return None


def filter_discussion_links(all_links):
    pattern = re.compile(
        r"^https://www\.examtopics\.com/discussions/"
        r"[^/]+/view/"
        r"\d+-exam-[^/]+-topic-\d+-question-\d+-discussion/?$"
    )

    filtered_links = []

    for link in all_links:
        if pattern.match(link):
            filtered_links.append(link)
    
    return filtered_links

def filter_exam_links(exam_name: str, all_links: list[str]) -> list[str]:
    exam_name = exam_name.lower()

    def check(url):
        exam_id = _extract_exam_id(url)
        return url if exam_id and exam_name in exam_id else None

    with ThreadPoolExecutor() as ex:
        results = ex.map(check, all_links)

    return [r for r in results if r]
