from flask import (
    Blueprint, current_app, render_template,
    request, redirect, url_for, abort, session,
    Response, stream_with_context, send_file, after_this_request
)
from .providers import get_provider_exams
from .questions import get_questions
from .anki import generate_anki_file
import json, os
from .local_cache import questions_cache_key, cache
from .filter import filter_questions_for_test

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

@bp.route("/<provider>/<exam_code>/test", methods=["GET"])
def test_start(provider, exam_code):
    """Start test - przekierowuje do pierwszego pytania"""
    cache_key = questions_cache_key(provider, exam_code)
    questions = cache.get(cache_key)
    if not questions:
        return "Questions not loaded", 400

    valid_questions = filter_questions_for_test(questions)
    if not valid_questions:
        return "No valid questions with choices found", 400

    return redirect(url_for("exam.test_question", provider=provider, exam_code=exam_code, q_index=0))

@bp.route("/<provider>/<exam_code>/test/<int:q_index>", methods=["GET", "POST"])
def test_question(provider, exam_code, q_index):
    cache_key = questions_cache_key(provider, exam_code)
    questions = cache.get(cache_key)
    if not questions:
        return "Questions not loaded", 400

    valid_questions = filter_questions_for_test(questions)
    if not valid_questions:
        return "No valid questions with choices found", 400

    if q_index < 0 or q_index >= len(valid_questions):
        return "Question not found", 404

    q = valid_questions[q_index]

    if request.method == "POST":
        user_answers = request.session.get("user_answers", {})
        ans = request.form.get("answer")
        if ans:
            user_answers[str(q_index)] = ans
            request.session["user_answers"] = user_answers

        if q_index + 1 < len(valid_questions):
            return redirect(url_for("exam.test_question", provider=provider, exam_code=exam_code, q_index=q_index+1))
        else:
            return redirect(url_for("exam.test_result", provider=provider, exam_code=exam_code))

    return render_template(
        "test_question.html",
        provider_name=current_app.config["PROVIDERS"][provider],
        exam_code=exam_code,
        question=q,
        q_index=q_index,
        total=len(valid_questions)
    )


@bp.route("/<provider>/<exam_code>/test/result", methods=["GET"])
def test_result(provider, exam_code):
    cache_key = questions_cache_key(provider, exam_code)
    questions = cache.get(cache_key)
    if not questions:
        return "Questions not loaded", 400

    valid_questions = [q for q in questions if q.get("choices")]
    if not valid_questions:
        return "No valid questions with choices found", 400

    user_answers = request.session.get("user_answers", {})

    correct_count = 0
    for idx, q in enumerate(valid_questions):
        correct_ans = None
        if q.get("answer"):
            soup = BeautifulSoup(q["answer"], "html.parser")
            correct_ans = soup.get_text(strip=True)
        if correct_ans and user_answers.get(str(idx)) == correct_ans:
            correct_count += 1

    request.session.pop("user_answers", None)

    return render_template(
        "test_result.html",
        provider_name=current_app.config["PROVIDERS"][provider],
        exam_code=exam_code,
        total=len(valid_questions),
        correct=correct_count
    )


@bp.route("/<provider>/<exam_code>/learn")
def learn_mode(provider, exam_code):
    cache_key = questions_cache_key(provider, exam_code)
    questions = cache.get(cache_key)

    if not questions:
        return "Questions not loaded", 400

    return render_template(
        "learn.html",
        provider_key=provider,
        exam_code=exam_code,
        provider_name=current_app.config["PROVIDERS"][provider],
        questions=questions,
    )


