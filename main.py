import sqlalchemy
from flask import Flask, jsonify, render_template, request, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from sqlalchemy.orm import relationship
from form import RegisterForm, LoginForm, CafeForm
from functools import wraps
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# Connect to Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafes.db'
db = SQLAlchemy()
db.init_app(app)


# Cafe TABLE Configuration
class Cafe(db.Model):
    __tablename__ = "cafes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    map_url = db.Column(db.String(500), nullable=False)
    img_url = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(250), nullable=False)
    seats = db.Column(db.String(250), nullable=False)
    has_toilet = db.Column(db.Boolean, nullable=False)
    has_wifi = db.Column(db.Boolean, nullable=False)
    has_sockets = db.Column(db.Boolean, nullable=False)
    can_take_calls = db.Column(db.Boolean, nullable=False)
    coffee_price = db.Column(db.String(250), nullable=True)
    author = relationship("User", back_populates="cafes")
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    cafes = relationship("Cafe", back_populates="author")
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(250), nullable=False)


with app.app_context():
    db.create_all()


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def home():
    return redirect(url_for("get_all_cafes"))


# HTTP GET - Read Record
@app.route("/random")
def get_random_cafe():
    result = db.session.execute(db.select(Cafe))
    all_cafes = result.scalars().all()
    random_cafe = random.choice(all_cafes)
    return jsonify(cafe=random_cafe.to_dict())


@app.route("/all")
def get_all_cafes():
    result = db.session.execute(db.select(Cafe).order_by(Cafe.name))
    all_cafes = result.scalars().all()
    return render_template("index.html", cafes=all_cafes, current_user=current_user)


@app.route("/cafe/<int:cafe_id>", methods=["GET", "POST"])
def get_cafe(cafe_id):
    result = db.session.execute(db.select(Cafe).where(Cafe.id == cafe_id))
    cafe = result.scalar()
    return render_template("cafe.html", cafe=cafe, current_user=current_user)


@app.route("/search")
def search_cafe():
    location = request.args.get("loc")
    result = db.session.execute(db.select(Cafe).where(Cafe.location == location))
    all_cafes = result.scalars().all()
    if all_cafes:
        return render_template("search.html", cafes=all_cafes)
    return jsonify(error={"Not Found": "Sorry no cafe at that location."})


# HTTP POST - Create Record
@app.route("/add", methods=["GET", "POST"])
def add_cafe():
    form = CafeForm()
    if form.validate_on_submit():
        new_cafe = Cafe(
            name=form.name.data,
            map_url=form.map_url.data,
            img_url=form.img_url.data,
            location=form.location.data,
            has_sockets=form.has_sockets.data,
            has_toilet=form.has_toilet.data,
            has_wifi=form.has_wifi.data,
            can_take_calls=form.can_take_calls.data,
            seats=form.seats.data,
            coffee_price=form.coffee_price.data,
            author=current_user
        )
        db.session.add(new_cafe)
        db.session.commit()
        return redirect(url_for("get_all_cafes"))
    return render_template("add_cafe.html", form=form, current_user=current_user)


# HTTP PUT/PATCH - Update Record
@app.route("/update-price/<int:cafe_id>", methods=["PATCH"])
def update_price(cafe_id):
    new_price = request.args.get("new_price")
    cafe_to_update = db.session.get(Cafe, cafe_id)
    if cafe_to_update:
        cafe_to_update.coffee_price = new_price
        db.session.commit()
        return jsonify(success="Successfully updated the price."), 200
    else:
        return jsonify(error={"Not Found": "Cannot found id in the database."}), 400


# HTTP DELETE - Delete Record
@app.route("/report-closed/<int:cafe_id>")
def delete_cafe(cafe_id):
    cafe_to_delete = db.get_or_404(Cafe, cafe_id)
    db.session.delete(cafe_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_cafes'))
# def delete_cafe(cafe_id):
#     api_key = request.args.get("api-key")
#     cafe_to_delete = db.session.get(Cafe, cafe_id)
#     if cafe_to_delete and api_key == "TopSecretAPIKey":
#         db.session.delete(cafe_to_delete)
#         db.session.commit()
#         return jsonify(success="Successfully deleted the cafe."), 200
#     elif api_key != "TopSecretAPIKey":
#         return jsonify(error="Incorrect api_key"), 403
#     else:
#         return jsonify(error={"Not Found": "Cannot found id in the database."}), 404


@app.route("/signup", methods=["GET", "POST"])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=form.password.data
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("get_all_cafes"))
    return render_template("signup.html", form=form, current_user=current_user)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        password = form.password.data
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()
        if user.password == password:
            login_user(user)
            return redirect(url_for("get_all_cafes"))
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_cafes'))


if __name__ == '__main__':
    app.run(debug=True)
