from bs4 import BeautifulSoup
import json
import requests
import re, os
from urllib.parse import urlparse

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

    return question_body.prettify()

def _extract_answer_html(soup: BeautifulSoup, url):
    answer_body = soup.find("span", class_="correct-answer")

    _save_images(url, answer_body)

    return answer_body.prettify()

def _save_images(url, body):
    if body is None:
        return None

    images = body.find_all("img")
    for _, img in enumerate(images, 1):
        src = img["src"]

        if src.startswith("http://") or src.startswith("https://"):
            parsed = urlparse(src)
            src_path = parsed.path.lstrip("/")  
        else:
            src_path = src.lstrip("/")

        img_url = url + src_path if not src.startswith("http") else src
        img_data = requests.get(img_url).content

        folder = os.path.dirname(src_path)
        os.makedirs(folder, exist_ok=True)

        img_filename = os.path.basename(src_path)
        img_path = os.path.join(folder, img_filename)

        with open(img_path, "wb") as f:
            f.write(img_data)

        img["src"] = src_path
        
        print(src_path) #debug FIXME

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