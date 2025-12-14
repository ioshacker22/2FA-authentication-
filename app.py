from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel, gettext as _
import pyotp, qrcode, io, base64, bcrypt, os, json
import pyttsx3

# 
#  FLASK APPLICATION SETUP
# 
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")  # Secret key for sessions & security


# 
#  DATABASE CONFIGURATION
# 
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///2fa.db"
db = SQLAlchemy(app)


# 
#  BABEL (LANGUAGE / INTERNATIONALIZATION) SETUP
# 
app.config["BABEL_DEFAULT_LOCALE"] = "en"
babel = Babel(app)

@babel.localeselector
def get_locale():
    """
    Determines which language to use.
    If ?lang=xx is in the URL, save it in the session.
    Otherwise, default to the last selected language or English.
    """
    if 'lang' in request.args:
        session['lang'] = request.args['lang']
    return session.get('lang', 'en')


# 
#  DATABASE MODELS
# 
class User(db.Model):
    """
    Stores registered users:
    - username (unique)
    - hashed password
    - secret (base32 TOTP secret for the main account)
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    secret = db.Column(db.String(32), nullable=False)


class Token(db.Model):
    """
    Stores additional 2FA tokens saved by the user:
    - user_id (belongs to User)
    - service name
    - secret (base32 TOTP secret)
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    service = db.Column(db.String(100), nullable=False)
    secret = db.Column(db.String(32), nullable=False)


# Create tables if they don't exist
with app.app_context():
    db.create_all()


# 
#  HELPER FUNCTIONS
# 
def generate_qr_uri(username, secret):
    """
    Generates a QR code (Base64 PNG) for scanning into Google Authenticator,
    Authy, or any TOTP app.
    """
    otp_uri = pyotp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name="My2FAApp"
    )

    img = qrcode.make(otp_uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")

    return base64.b64encode(buffer.getvalue()).decode()


def read_token(token):
    """
    Uses text-to-speech to read the 2FA code aloud.
    Helps users with accessibility needs.
    """
    engine = pyttsx3.init()
    engine.say(f"Your authentication code is {', '.join(token)}")
    engine.runAndWait()


# 
#  ROUTES
# 

@app.route("/")
def home():
    """Landing page."""
    return render_template("home.html")


# --------------------------- REGISTER ---------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Handles user registration:
    - Validates unique username
    - Hashes password
    - Generates a new TOTP secret
    - Displays QR code for setup
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check user exists
        if User.query.filter_by(username=username).first():
            return _("Username already exists")

        # Secure the password
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # Create user secret
        secret = pyotp.random_base32()

        # Save new user
        new_user = User(username=username, password=hashed_pw, secret=secret)
        db.session.add(new_user)
        db.session.commit()

        # Show QR code for scanning
        qr_code = generate_qr_uri(username, secret)
        return render_template("qr.html", qr_code=qr_code, username=username)

    return render_template("register.html")


# --------------------------- LOGIN ------------------------------ #
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Verifies username & password.
    If correct, redirect to token verification step.
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if not user or not bcrypt.checkpw(password.encode(), user.password.encode()):
            return _("Invalid username or password")

        # Store login session temporarily (until token step)
        session["username"] = username
        return render_template("verify.html", username=username)

    return render_template("login.html")


# ----------------------- TOKEN VERIFICATION ---------------------- #
@app.route("/verify", methods=["POST"])
def verify():
    """
    Verifies the TOTP token entered during login.
    If valid:
      - reads the token (optional)
      - logs the user into their dashboard
    """
    username = request.form["username"]
    token = request.form["token"]

    user = User.query.filter_by(username=username).first()
    if not user:
        return _("User not found")

    totp = pyotp.TOTP(user.secret)

    # Validate TOTP
    if totp.verify(token):
        read_token(token)
        session["username"] = username
        return redirect(url_for("dashboard"))
    else:
        return _("Invalid token. Please try again.")


# --------------------------- DASHBOARD --------------------------- #
@app.route("/dashboard")
def dashboard():
    """
    Displays saved service tokens for the logged-in user.
    """
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["username"]).first()
    tokens = Token.query.filter_by(user_id=user.id).all()

    return render_template("dashboard.html",
                           username=user.username,
                           tokens=tokens,
                           pyotp=pyotp)


# -------------------------- ADD TOKEN ----------------------------  #
@app.route("/add_token", methods=["GET", "POST"])
def add_token():
    """
    Allows users to add a new 2FA token for a service.
    Generates a new secret automatically.
    """
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


# ------------------------ DELETE TOKEN --------------------------- #
@app.route("/delete_token/<int:token_id>")
def delete_token(token_id):
    """
    Deletes a saved token from the user's dashboard.
    """
    if "username" not in session:
        return redirect(url_for("login"))

    token = Token.query.get(token_id)
    if token:
        db.session.delete(token)
        db.session.commit()

    return redirect(url_for("dashboard"))


# ------------------------- IMPORT TOKENS -------------------------- #
@app.route("/import_token", methods=["GET", "POST"])
def import_token():
    """
    Allows users to upload a JSON backup file to restore saved tokens.
    """
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


# ------------------------- EXPORT TOKENS --------------------------  #
@app.route("/export_tokens")
def export_tokens():
    """
    Exports the user's saved tokens into a downloadable JSON file.
    """
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["username"]).first()
    tokens = Token.query.filter_by(user_id=user.id).all()

    data = {
        "tokens": [{"service": t.service, "secret": t.secret} for t in tokens]
    }

    return app.response_class(
        response=json.dumps(data, indent=4),
        mimetype='application/json',
        headers={"Content-Disposition": "attachment;filename=tokens_backup.json"}
    )


# --------------------------- LOGOUT ------------------------------ #
@app.route("/logout")
def logout():
    """Logs the user out and clears their session."""
    session.clear()
    return redirect(url_for("home"))


#  RUN APP #

if __name__ == "__main__":
    app.run(debug=True)
