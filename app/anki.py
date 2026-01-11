import genanki, random, string, tempfile, os
from bs4 import BeautifulSoup, Tag

def generate_anki_file(questions, exam_code, base_url=""):
    deck_id = int("".join(random.choices(string.digits, k=10)))
    deck_name = f"{exam_code}"

    deck = genanki.Deck(
        deck_id=deck_id,
        name=deck_name
    )

    model = genanki.Model(
        model_id=random.randint(1_000_000, 9_999_999),
        name=f"{exam_code}_model",
        fields=[
            {"name": "Question"},
            {"name": "Answer"}
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Question}}",
                "afmt": "{{FrontSide}}<hr id='answer'>{{Answer}}"
            }
        ],
        css="""
        .card { font-family: arial; font-size: 14px; text-align: left; }
        img { max-width: 100%; height: auto; }
        """
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        media_files = []

        for q in questions:
            #### FRONT ###
            question_html = q.get("question_html", "")
            soup = BeautifulSoup(question_html, "html.parser")

            media_files.extend(
                anki_collect_images_and_fix_html(
                    soup,
                    media_root="assets/media" #FIXME hardcoded
                )
            )

            choices_html = ""
            if q.get("choices"):
                choices_html = "<ul>" + "".join(
                    f"<li><strong>{c['letter']}.</strong> {c['text']}</li>"
                    for c in q["choices"]
                ) + "</ul>"

            front = str(soup) + choices_html

            #### BACK ###
            voted_answers_html = ""
            if q.get("voted_answers"):
                voted_answers_html = (
                    "<p><strong>Voted Answers:</strong></p><ul>"
                    + "".join(f"<li>{v['voted_answers']}: {v['vote_count']} vote{'s' if v['vote_count'] != 1 else ''}"
                        + (" ⭐" if v.get("is_most_voted") else "")
                        + "</li>"
                        for v in q["voted_answers"]
                    )
                    + "</ul>"
                )

            raw_answer = q.get("answer", "")
            fixed_answer = add_br_if_answer_starts_with_image(raw_answer)

            answer_html = f"<p><strong>Suggested answer:</strong>{fixed_answer}</p>"

            answer_soup = BeautifulSoup(answer_html, "html.parser")

            media_files.extend(
                anki_collect_images_and_fix_html(
                    answer_soup,
                    media_root="assets/media"
                )
            )

            back = str(answer_soup) + voted_answers_html

            back += f"<p><a href='{q.get('link', '')}' target='_blank'>See this question on exam topics</a></p>"

            note = genanki.Note(model=model, fields=[front, back])
            deck.add_note(note)

        fd, output_path = tempfile.mkstemp(suffix=".apkg", prefix=f"{exam_code}_")
        os.close(fd)

        package = genanki.Package(deck)
        package.media_files = media_files
        package.write_to_file(output_path)

        return output_path
    

def anki_collect_images_and_fix_html(soup, media_root):

    media_files = []

    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue

        filename = os.path.basename(src)
        full_path = os.path.join(media_root, src)

        if os.path.exists(full_path):
            media_files.append(full_path)
            img["src"] = filename
        else:
            print(f"⚠️ Image not found on disk: {full_path}")

    return media_files


from bs4 import BeautifulSoup, Tag, NavigableString


def first_real_tag(node):
    for child in node.children:
        if isinstance(child, NavigableString):
            if child.strip():
                return None
            continue
        if isinstance(child, Tag):
            return child
    return None


def contains_img(tag):
    if tag.name == "img":
        return True
    return any(
        isinstance(c, Tag) and contains_img(c)
        for c in tag.children
    )


def add_br_if_answer_starts_with_image(answer_html: str) -> str:
    soup = BeautifulSoup(answer_html or "", "html.parser")

    first = first_real_tag(soup)
    if not first:
        return str(soup)

    # jeśli już zaczyna się od <br>, nic nie rób
    if first.name == "br":
        return str(soup)

    # jeśli pierwszy realny element zawiera <img>
    if contains_img(first):
        soup.insert(0, soup.new_tag("br"))

    return str(soup)
