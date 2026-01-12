from flask import (
    Blueprint, current_app, render_template,
    request, redirect, url_for, abort, session,
    Response, stream_with_context, send_file, after_this_request,
    send_from_directory, jsonify
)
from .providers import get_provider_exams
from .questions import get_questions
from .anki import generate_anki_file, add_br_if_answer_starts_with_image
import json, os
from .local_cache import questions_cache_key, cache
from .filter import filter_questions_for_test
from bs4 import BeautifulSoup
import random
import re
from .utils import _make_asset_paths_absolute

bp = Blueprint("main", __name__)


@bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        provider = request.form.get("provider")
        if provider not in current_app.config["PROVIDERS"]:
            abort(404)
        return redirect(url_for("main.provider", provider=provider))

    return render_template("index.html", options=current_app.config["PROVIDERS"])


@bp.route("/<provider>", methods=["GET", "POST"])
def provider(provider):
    providers = current_app.config["PROVIDERS"]
    if provider not in providers:
        abort(404)

    exams = get_provider_exams(
        base_url=current_app.config["BASE_URL"],
        headers=current_app.config["HEADERS"],
        provider_name=provider,
    )

    if request.method == "POST":
        exam_code = request.form.get("exam")
        if exam_code not in exams:
            abort(404)

        session["exam_name"] = exams[exam_code]
        session["exam_code"] = exam_code
        session["provider"] = provider

        return redirect(
            url_for(
                "main.exam_detail",
                provider=provider,
                exam_code=exam_code,
            )
        )

    return render_template(
        "provider.html",
        provider_name=providers[provider],
        exams=exams,
        provider_key=provider
    )


@bp.route("/<provider>/<exam_code>")
def exam_detail(provider, exam_code):
    exam_name = session.get("exam_name")
    
    return render_template(
        "exam.html",
        provider_key=provider,
        provider_name=current_app.config["PROVIDERS"][provider],
        exam_code=exam_code,
        exam_name=exam_name,
    )

@bp.route("/api/questions/progress")
def questions_progress():

    def generate():
        for event in get_questions(exam_provider=session["provider"], exam_code=session["exam_code"], url=current_app.config["BASE_URL"], headers=current_app.config["HEADERS"], caching=current_app.config["CACHE_ENABLED"]): 
            if event.get("type") == "done":
                cache_key = questions_cache_key(session["provider"], session["exam_code"])
                cache.set(cache_key, event["questions"])
            
            yield f"data: {json.dumps(event)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream"
    )

@bp.route("/<provider>/<exam_code>/anki")
def download_anki(provider, exam_code):
    cache_key = questions_cache_key(provider, exam_code)
    questions = cache.get(cache_key)

    if not questions:
        return "No questions loaded yet", 400

    file_path = None

    file_path = generate_anki_file(questions, exam_code)


    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            current_app.logger.error(f"Cleanup failed: {e}")
        return response


    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"{exam_code}.apkg"
    )

@bp.route("/<provider>/<exam_code>/test", methods=["GET", "POST"])
def test_start(provider, exam_code):
    cache_key = questions_cache_key(provider, exam_code)
    questions = cache.get(cache_key)
    if not questions:
        return "Questions not loaded", 400

    valid_questions, rejected_questions = filter_questions_for_test(questions)
    if not valid_questions:
        return "No valid questions with choices found", 400

    if request.method == "POST":
        try:
            num_questions = int(request.form.get("num_questions", len(valid_questions)))
        except ValueError:
            num_questions = len(valid_questions)

        num_questions = min(num_questions, len(valid_questions))

        chosen_indices = random.sample(range(len(valid_questions)), num_questions)

        session["test_question_order"] = chosen_indices
        session["user_answers"] = {}
        session["test_num_questions"] = num_questions

        return redirect(url_for(
            "main.test_question",
            provider=provider,
            exam_code=exam_code,
            q_index=0
        ))

    return render_template(
        "test_start.html",
        provider=provider,
        exam_code=exam_code,
        provider_name=current_app.config["PROVIDERS"][provider],
        total_questions=len(valid_questions),
        rejected_count=rejected_questions,
        exam_name=session["exam_name"]
    )


@bp.route("/<provider>/<exam_code>/test/<int:q_index>", methods=["GET", "POST"])
def test_question(provider, exam_code, q_index):
    chosen_indices = session.get("test_question_order")
    if not chosen_indices:
        return redirect(url_for("main.test_start", provider=provider, exam_code=exam_code))

    cache_key = questions_cache_key(provider, exam_code)
    questions = cache.get(cache_key)
    valid_questions, rejected_count = filter_questions_for_test(questions)

    if q_index < 0 or q_index >= len(chosen_indices):
        return "Question not found", 404

    idx = chosen_indices[q_index]
    q = valid_questions[idx]

    q_html = q.get("question_html")
    q["question_html"] = _make_asset_paths_absolute(q_html)
    answer_html = q.get("answer")
    q["answer"] = _make_asset_paths_absolute(answer_html)

    correct_text = BeautifulSoup(q.get("answer", ""), "html.parser").get_text(strip=True)
    correct_letters = re.findall(r"[A-Z]", correct_text)
    is_multi = len(correct_letters) > 1

    if request.method == "POST":
        user_answers = session.get("user_answers", {})
        ans_list = request.form.getlist("answer")
        if ans_list:
            user_answers[str(q_index)] = ans_list
            session["user_answers"] = user_answers

        if q_index + 1 < len(chosen_indices):
            return redirect(url_for(
                "main.test_question",
                provider=provider,
                exam_code=exam_code,
                q_index=q_index+1
            ))
        else:
            return redirect(url_for("main.test_result", provider=provider, exam_code=exam_code))

    user_answers = session.get("user_answers", {})
    selected_answers = user_answers.get(str(q_index), [])

    return render_template(
        "test_question.html",
        provider_name=current_app.config["PROVIDERS"][provider],
        provider=provider,
        exam_code=exam_code,
        question=q,
        q_index=q_index,
        total=len(chosen_indices),
        rejected_count=rejected_count,
        is_multi=is_multi,
        selected_answers=selected_answers
    )

@bp.route("/<provider>/<exam_code>/test/result", methods=["GET"])
def test_result(provider, exam_code):
    chosen_indices = session.get("test_question_order")
    if not chosen_indices:
        return "Test session expired or no questions selected", 400

    cache_key = questions_cache_key(provider, exam_code)
    questions = cache.get(cache_key)
    valid_questions, _ = filter_questions_for_test(questions)
    user_answers = session.get("user_answers", {})

    total_points = 0.0
    full_correct = 0
    for q_num, idx in enumerate(chosen_indices):
        q = valid_questions[idx]
        correct_text = BeautifulSoup(q.get("answer", ""), "html.parser").get_text(strip=True)
        correct_letters = re.findall(r"[A-Z]", correct_text)
        correct_set = set(correct_letters)

        user_sel = user_answers.get(str(q_num), [])
        if isinstance(user_sel, str):
            user_set = {user_sel}
        elif isinstance(user_sel, (list, tuple)):
            user_set = set(user_sel)
        else:
            user_set = set()

        if not correct_set:
            continue

        if user_set == correct_set and user_set:
            total_points += 1.0
            full_correct += 1
        else:
            inter = user_set & correct_set
            if inter:
                total_points += len(inter) / len(correct_set)

    session.pop("user_answers", None)
    session.pop("test_question_order", None)
    session.pop("test_num_questions", None)

    return render_template(
        "test_result.html",
        provider_name=current_app.config["PROVIDERS"][provider],
        provider=provider,
        exam_code=exam_code,
        total=len(chosen_indices),
        points=total_points,
        max_points=len(chosen_indices),
        full_correct=full_correct
    )


@bp.route("/<provider>/<exam_code>/learn")
def learn_mode(provider, exam_code):
    cache_key = questions_cache_key(provider, exam_code)
    questions = cache.get(cache_key)

    if not questions:
        return "Questions not loaded", 400
    for qq in questions:
        qq["question_html"] = _make_asset_paths_absolute(qq.get("question_html"))
        qq["answer"] = _make_asset_paths_absolute(qq.get("answer"))
    sorted_qs = sorted(questions, key=lambda q: (q.get("topic_number", 0), q.get("question_number", 0)))

    processed = []
    topics = []
    for i, q in enumerate(sorted_qs):
        topic = q.get("topic_number")
        if topic not in topics:
            topics.append(topic)

        correct_text = BeautifulSoup(q.get("answer", ""), "html.parser").get_text(strip=True)
        correct_letters = re.findall(r"[A-Z]", correct_text)

        answer_html = add_br_if_answer_starts_with_image(q.get("answer", ""))

        processed.append({
            "idx": i,
            "topic_number": q.get("topic_number"),
            "question_number": q.get("question_number"),
            "question_html": q.get("question_html", ""),
            "choices": q.get("choices", []),
            "answer_html": answer_html,
            "correct_letters": correct_letters,
            "voted_answers": q.get("voted_answers", []),
            "comments": q.get("comments", []),
            "link": q.get("link", ""),
        })

    return render_template(
        "learn.html",
        provider_key=provider,
        exam_code=exam_code,
        provider_name=current_app.config["PROVIDERS"][provider],
        questions=processed,
        topics=sorted(topics),
        exam_name=session["exam_name"],
    )


@bp.route("/<provider>/<exam_code>/learn/data")
def learn_data(provider, exam_code):
    cache_key = questions_cache_key(provider, exam_code)
    questions = cache.get(cache_key)
    if not questions:
        return jsonify({"ok": False, "error": "Questions not loaded"}), 400

    # normalize images
    for qq in questions:
        qq["question_html"] = _make_asset_paths_absolute(qq.get("question_html"))
        qq["answer"] = _make_asset_paths_absolute(qq.get("answer"))

    sorted_qs = sorted(questions, key=lambda q: (q.get("topic_number", 0), q.get("question_number", 0)))

    processed = []
    topics = []
    for i, q in enumerate(sorted_qs):
        topic = q.get("topic_number")
        if topic not in topics:
            topics.append(topic)

        correct_text = BeautifulSoup(q.get("answer", ""), "html.parser").get_text(strip=True)
        correct_letters = re.findall(r"[A-Z]", correct_text)
        answer_html = add_br_if_answer_starts_with_image(q.get("answer", ""))

        processed.append({
            "idx": i,
            "topic_number": q.get("topic_number"),
            "question_number": q.get("question_number"),
            "question_html": q.get("question_html", ""),
            "choices": q.get("choices", []),
            "answer_html": answer_html,
            "correct_letters": correct_letters,
            "voted_answers": q.get("voted_answers", []),
            "comments": q.get("comments", []),
            "link": q.get("link", ""),
        })

    return jsonify({"ok": True, "questions": processed, "topics": sorted(topics)})



@bp.route("/<provider>/<exam_code>/learn/save", methods=["POST"])
def learn_save(provider, exam_code):
    data = request.get_json(silent=True) or {}
    q_idx = data.get("q_idx")
    answers = data.get("answers")
    shown = data.get("shown", False)

    if q_idx is None:
        return {"ok": False, "error": "missing q_idx"}, 400

    learn_answers = session.get("learn_answers", {})
    learn_answers[str(q_idx)] = {
        "answers": answers,
        "shown": bool(shown)
    }
    session["learn_answers"] = learn_answers

    return {"ok": True}


@bp.route('/assets/<path:filename>')
def assets(filename):
    assets_dir = os.path.abspath(os.path.join(current_app.root_path, '..', 'assets'))
    return send_from_directory(assets_dir, filename)


