from flask import Blueprint, render_template, abort
from flask_babel import _
from app.models import SharedLink, Book
from datetime import datetime

bp = Blueprint('share', __name__, url_prefix='/share')


@bp.route('/<token>/')
def view(token):
    link = SharedLink.query.filter_by(token=token).first_or_404()
    if not link.is_valid():
        abort(404)
    books = Book.query.filter_by(library_id=link.library_id).all()
    return render_template('share/book_list.html', books=books, link=link)


@bp.route('/<token>/book/<int:book_id>')
def book_detail(token, book_id):
    link = SharedLink.query.filter_by(token=token).first_or_404()
    if not link.is_valid():
        abort(404)
    book = Book.query.filter_by(id=book_id, library_id=link.library_id).first_or_404()
    return render_template('share/book_detail.html', book=book, link=link)
