from app import app
from flask import render_template


@app.route('/')
def home():
    return render_template('index.html')

@app.route("/books/add/", methods=["GET", "POST"])
def book_add():
    form = BookForm()
    genres = [genre[0] for genre in books.get_unique_genres()]
    if form.validate_on_submit():
        new_book_data = {
            'title': form.title.data,
            'author': form.author.data,
            'genre': form.genre.data,
            'year': form.year.data
        }

        if form.cover.data:
            f = form.cover.data
            cover_filename = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], cover_filename))
            new_book_data['cover'] = cover_filename

        books.create(new_book_data)
        flash("Książka została pomyślnie dodana!", "success")
        return redirect(url_for("library"))

    return render_template("book_add.html", form=form, genres=genres)