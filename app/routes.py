from flask import (
    Blueprint, current_app, render_template,
    request, redirect, url_for, abort, session
)

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

    exams = get_provider_exams(
        base_url=current_app.config["BASIC_URL"],
        headers=current_app.config["HEADERS"],
        provider_name=provider,
    )

    if request.method == "POST":
        exam_code = request.form.get("exam")
        if exam_code not in exams:
            abort(404)

        session["exam_name"] = exams[exam_code]

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

    if not exam_code:
        abort(400)

    return render_template(
        "exam.html",
        provider_key=provider,
        provider_name=current_app.config["PROVIDERS"][provider],
        exam_code=exam_code,
        exam_name=exam_name
    )
