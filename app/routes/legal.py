from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_babel import get_locale


bp = Blueprint("legal", __name__, url_prefix="/legal")


@bp.route("/gpdr", methods=["GET"])
def gpdr():
    lang = str(get_locale())
    if lang.startswith('en'):
        return render_template("legal/gpdr_en.html")
    return render_template("legal/gpdr_pl.html")


@bp.route("/privacy", methods=["GET"])
def privacy():
    return render_template("legal/privacy_pl.html")


@bp.route("/terms", methods=["GET"])
def terms():
    return render_template("legal/terms_pl.html")


@bp.route("/cookies", methods=["GET"])
def cookies():
    return render_template("legal/cookie_pl.html")
