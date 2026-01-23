from bs4 import BeautifulSoup
import json
import requests
import re, os, uuid
from urllib.parse import urlparse, urljoin

def _extract_discussion_title(soup: BeautifulSoup) -> str | None:
    h1 = soup.select_one(".discussion-list-header h1")
    if not h1:
        return None

    return h1.get_text(strip=True)

def _get_discussion_numbers(soup: BeautifulSoup) -> tuple:
    h1 = _extract_discussion_title(soup)
    matching = re.search(r"topic (\d+) question (\d+)", h1)

    if matching:
        topic_number = int(matching.group(1))
        question_number = int(matching.group(2))

    return topic_number, question_number

def _extract_choices(soup: BeautifulSoup):
    choices = []

    for li in soup.select(".question-choices-container li.multi-choice-item"):
        letter_span = li.select_one(".multi-choice-letter")
        letter = letter_span["data-choice-letter"] if letter_span else None

        if letter_span:
            letter_span.extract()

        text = li.get_text(strip=True)

        choices.append({
            "letter": letter,
            "text": text
        })

    return choices

def _extract_voted_answers(soup: BeautifulSoup):
    result = []

    scripts = soup.select(
        ".voted-answers-tally script[type='application/json']"
    )

    for script in scripts:
        try:
            data = json.loads(script.string)
            result.extend(data)
        except Exception:
            pass

    return result

def _extract_comments(soup: BeautifulSoup):
    comments_data = []

    for comment in soup.select("div.comment-container"):
        username_tag = comment.select_one(".comment-username")
        username = username_tag.get_text(strip=True) if username_tag else None

        badge_tag = comment.select_one(".badge")
        badge = badge_tag.get_text(strip=True) if badge_tag else None

        date_tag = comment.select_one(".comment-date")
        date = date_tag["title"] if date_tag and date_tag.has_attr("title") else None

        content_tag = comment.select_one(".comment-content")
        content = content_tag.get_text(strip=True) if content_tag else None

        vote_tag = comment.select_one(".upvote-count")
        votes = int(vote_tag.get_text(strip=True)) if vote_tag else 0

        comments_data.append({
            "username": username,
            "badge": badge,
            "date": date,
            "content": content,
            "votes": votes
        })

    return comments_data

def _extract_question_html(soup: BeautifulSoup, url):
    question_body = soup.find("div", class_="question-body")
   
    _save_images(url, question_body)

    if question_body:
        p_tag = question_body.find("p", class_="card-text")
        if p_tag:
            return p_tag.prettify()

    return None

def _extract_answer_html(soup: BeautifulSoup, url):
    answer_body = soup.find("span", class_="correct-answer")

    _save_images(url, answer_body)

    return answer_body.prettify()


def _save_images(base_url, body, media_folder="assets/media"):

    if body is None:
        return []

    saved_files = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    images = body.find_all("img")
    for img in images:
        src = img.get("src")
        if not src or "_unique_local_name" in src:
            continue

        if not src.startswith("http"):
            img_url = "https://www.examtopics.com/" + src
        else:
            img_url = src

        try:
            r = requests.get(img_url, headers=headers)
            r.raise_for_status()
            img_data = r.content
        except Exception as e:
            try: # try again on img.examtopics.com
                img_url = f"https://img.examtopics.com/{src.lstrip('/')}"
                r = requests.get(img_url, headers=headers)
                r.raise_for_status()
                img_data = r.content
            except Exception as e:
                print(f"⚠️ Failed to download image {img_url}: {e}")
                continue

        img_basename = os.path.basename(urlparse(src).path)
        folder = os.path.join(media_folder, os.path.dirname(urlparse(src).path).lstrip("/"))
        os.makedirs(folder, exist_ok=True)

        name, ext = os.path.splitext(img_basename)
        unique_name = f"{name}_{uuid.uuid4().hex}_unique_local_name{ext}"

        img_path = os.path.join(folder, unique_name)

        try:
            with open(img_path, "wb") as f:
                f.write(img_data)
        except Exception as e:
            print(f"⚠️ Failed to save image {img_path}: {e}")
            continue

        img["src"] = os.path.relpath(img_path, media_folder).replace("\\", "/")

        saved_files.append(img_path)

    return saved_files

        
def get_discussion(link, headers):
    response = requests.get(link, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    result = {
        'link': link,
        'title': _extract_discussion_title(soup),
        'topic_number': _get_discussion_numbers(soup)[0],
        'question_number': _get_discussion_numbers(soup)[1],
        'question_html': _extract_question_html(soup, link),
        'choices': _extract_choices(soup),
        'answer': _extract_answer_html(soup, link),
        'voted_answers': _extract_voted_answers(soup),
        'comments': _extract_comments(soup),
    }

    return result