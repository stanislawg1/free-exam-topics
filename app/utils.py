from bs4 import BeautifulSoup
import os

def _make_asset_paths_absolute(html: str | None) -> str | None:

    if not html:
        return html
    
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue

        img['src'] = "/assets/media/" + src #FIXME hardcoded

    return str(soup)