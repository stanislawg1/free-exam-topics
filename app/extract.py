from bs4 import BeautifulSoup
import json
import requests
import consts, re, os
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

    # każdy komentarz
    for comment in soup.select("div.comment-container"):
        # nick użytkownika
        username_tag = comment.select_one(".comment-username")
        username = username_tag.get_text(strip=True) if username_tag else None

        # badge (np. Highly Voted)
        badge_tag = comment.select_one(".badge")
        badge = badge_tag.get_text(strip=True) if badge_tag else None

        # data komentarza
        date_tag = comment.select_one(".comment-date")
        date = date_tag["title"] if date_tag and date_tag.has_attr("title") else None

        # treść komentarza
        content_tag = comment.select_one(".comment-content")
        content = content_tag.get_text(strip=True) if content_tag else None

        # liczba głosów
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

def _extract_question_html(soup: BeautifulSoup, images_output_folder="assets"):

    question_body = soup.find("div", class_="question-body")
    if question_body is None:
        return None

    images = question_body.find_all("img")
    for _, img in enumerate(images, 1):
        src = img["src"]

        if src.startswith("http://") or src.startswith("https://"):
            parsed = urlparse(src)
            src_path = parsed.path.lstrip("/")  
        else:
            src_path = src.lstrip("/")

        img_url = consts.URL + src_path if not src.startswith("http") else src
        img_data = requests.get(img_url).content

        folder = os.path.dirname(src_path)
        os.makedirs(folder, exist_ok=True)

        img_filename = os.path.basename(src_path)
        img_path = os.path.join(folder, img_filename)

        with open(img_path, "wb") as f:
            f.write(img_data)

        img["src"] = src_path

    return question_body.prettify()

def _extract_answer_html(soup: BeautifulSoup):
    answer_body = soup.find("span", class_="correct-answer")
    if answer_body is None:
        return None

    images = answer_body.find_all("img")
    for _, img in enumerate(images, 1):
        img_url = consts.URL + img["src"]
        img_data = requests.get(img_url).content

        local_path = img["src"].lstrip("/")  # rm starting /
        folder = os.path.dirname(local_path)
        os.makedirs(folder, exist_ok=True)

        img_filename = os.path.basename(local_path)
        img_path = os.path.join(folder, img_filename)

        with open(img_path, "wb") as f:
            f.write(img_data)

        img["src"] = local_path

    return answer_body.prettify()

def fetch_discussion_links(url, headers, exam_provider, page):
    links = get_links_from_page(f'{url}/{exam_provider}/{page}', headers=headers)
    return filter_discussion_links(links)

def fetch_discussion(link):
    return get_discussion(link)


def get_discussion(link):
    response = requests.get(link, headers=consts.HEADERS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    result = {
        'link': link,
        'title': _extract_discussion_title(soup),
        'topic_number': _get_discussion_numbers(soup)[0],
        'question_number': _get_discussion_numbers(soup)[1],
        'question_html': _extract_question_html(soup),
        'choices': _extract_choices(soup),
        'answer': _extract_answer_html(soup),
        'voted_answers': _extract_voted_answers(soup),
        'comments': _extract_comments(soup),
    }

    return result