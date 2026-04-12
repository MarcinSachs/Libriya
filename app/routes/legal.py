from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_babel import get_locale


bp = Blueprint("legal", __name__, url_prefix="/legal")


@bp.route("/privacy-policy", methods=["GET"])
def privacy_policy():
    lang = str(get_locale())
    if lang.startswith('en'):
        return render_template("legal/privacy-policy_en.html")
    return render_template("legal/privacy-policy_pl.html")


@bp.route("/terms", methods=["GET"])
def terms():
    lang = str(get_locale())
    if lang.startswith('en'):
        return render_template("legal/terms_en.html")
    return render_template("legal/terms_pl.html")


@bp.route("/cookies", methods=["GET"])
def cookies():
    lang = str(get_locale())
    if lang.startswith('en'):
        return render_template("legal/cookie_en.html")
    return render_template("legal/cookie_pl.html")
