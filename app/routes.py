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



@bp.route("/<provider>/<exam_code>/test")
def test_mode(provider, exam_code):
    cache_key = questions_cache_key(provider, exam_code)
    questions = cache.get(cache_key)
    if not questions:
        return "Questions not loaded", 400

    return render_template(
        "test.html",
        provider_key=provider,
        exam_code=exam_code,
        provider_name=current_app.config["PROVIDERS"][provider],
        questions=questions,
        mode="test"
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
        mode="learn"
    )


