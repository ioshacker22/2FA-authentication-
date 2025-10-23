from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel, gettext as _
import pyotp, qrcode, io, base64, bcrypt, os, json
import pyttsx3

## Flask setup ##
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

## Database setup ##
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///2fa.db"
db = SQLAlchemy(app)

## Babel setup  ##
app.config["BABEL_DEFAULT_LOCALE"] = "en"
babel = Babel(app)

@babel.localeselector
def get_locale():
    if 'lang' in request.args:
        session['lang'] = request.args['lang']
    return session.get('lang', 'en')

## Models  ##
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    secret = db.Column(db.String(32), nullable=False)

class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    service = db.Column(db.String(100), nullable=False)
    secret = db.Column(db.String(32), nullable=False)

with app.app_context():
    db.create_all()

## Helper: QR generation ##
def generate_qr_uri(username, secret):
    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name="My2FAApp")
    img = qrcode.make(otp_uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

## Helper: Text-to-speech ##
def read_token(token):
    engine = pyttsx3.init()
    engine.say(f"Your authentication code is {', '.join(token)}")
    engine.runAndWait()

## Routes ##
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            return _("Username already exists")

        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        secret = pyotp.random_base32()

        new_user = User(username=username, password=hashed_pw, secret=secret)
        db.session.add(new_user)
        db.session.commit()

        qr_code = generate_qr_uri(username, secret)
        return render_template("qr.html", qr_code=qr_code, username=username)
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if not user or not bcrypt.checkpw(password.encode(), user.password.encode()):
            return _("Invalid username or password")

        session["username"] = username
        return render_template("verify.html", username=username)
    return render_template("login.html")

@app.route("/verify", methods=["POST"])
def verify():
    username = request.form["username"]
    token = request.form["token"]
    user = User.query.filter_by(username=username).first()

    if not user:
        return _("User not found")

    totp = pyotp.TOTP(user.secret)
    if totp.verify(token):
        read_token(token)  # Accessibility
        session["username"] = username
        return redirect(url_for("dashboard"))
    else:
        return _("Invalid token. Please try again.")

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["username"]).first()
    tokens = Token.query.filter_by(user_id=user.id).all()
    return render_template("dashboard.html", username=user.username, tokens=tokens, pyotp=pyotp)

@app.route("/add_token", methods=["GET", "POST"])
def add_token():
    if "username" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        service = request.form["service"]
        secret = pyotp.random_base32()
        user = User.query.filter_by(username=session["username"]).first()
        token = Token(user_id=user.id, service=service, secret=secret)
        db.session.add(token)
        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("addToken.html")

@app.route("/delete_token/<int:token_id>")
def delete_token(token_id):
    if "username" not in session:
        return redirect(url_for("login"))
    token = Token.query.get(token_id)
    if token:
        db.session.delete(token)
        db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/import_token", methods=["GET", "POST"])
def import_token():
    if "username" not in session:
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["username"]).first()
    if request.method == "POST":
        file = request.files["backup"]
        data = json.load(file)
        for t in data.get("tokens", []):
            token = Token(user_id=user.id, service=t["service"], secret=t["secret"])
            db.session.add(token)
        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("import_token.html")

@app.route("/export_tokens")
def export_tokens():
    if "username" not in session:
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["username"]).first()
    tokens = Token.query.filter_by(user_id=user.id).all()
    data = {"tokens": [{"service": t.service, "secret": t.secret} for t in tokens]}
    return app.response_class(
        response=json.dumps(data, indent=4),
        mimetype='application/json',
        headers={"Content-Disposition": "attachment;filename=tokens_backup.json"}
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
