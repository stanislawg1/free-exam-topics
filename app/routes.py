from flask import Blueprint, render_template, current_app, abort, redirect, url_for, request
from .providers import get_provider_exams

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

    exams = get_provider_exams(                     #todo caching
        base_url=current_app.config["BASIC_URL"],
        headers=current_app.config["HEADERS"],
        provider_name=provider,
    )

    if request.method == "POST":
        exam = request.form.get("exam")
        if exam not in exams:
            abort(404)
        return redirect(url_for("main.exam_detail", provider=provider, exam_name=exam))

    return render_template(
        "provider.html",
        provider_name=providers[provider],
        exams=exams, 
        provider_key=provider
    )

@bp.route("/<provider>/<exam_name>")
def exam_detail(provider, exam_name):
    exams = get_provider_exams(                            #todo caching
        base_url=current_app.config["BASIC_URL"],
        headers=current_app.config["HEADERS"],
        provider_name=provider
    )

    print(exam_name)

    if exam_name not in exams:
        abort(404)

    return render_template(
        "exam.html",
        provider_key=provider,
        provider_name=current_app.config["PROVIDERS"][provider],
        exam_code=exam_name,
        exam_name=exams[exam_name]
    )
