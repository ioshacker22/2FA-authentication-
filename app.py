from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import pyotp, qrcode, io, base64, bcrypt, os, json

# FLASK APPLICATION SETUP
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key_change_in_production")

# DATABASE CONFIGURATION
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///2fa.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# DATABASE MODELS #
class User(db.Model):
    """
    Stores registered users:
    - username
    - hashed password
    - secret (base32 TOTP seed)
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    secret = db.Column(db.String(32), nullable=False)

class Token(db.Model):
    """
    Additional 2FA tokens saved by the user.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    service = db.Column(db.String(100), nullable=False)
    secret = db.Column(db.String(32), nullable=False)

with app.app_context():
    db.create_all()


# HELPER FUNCTIONS # 
def generate_qr_uri(username, secret):
    """Generate Base64 QR code for Google Authenticator."""
    otp_uri = pyotp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name="My2FAApp"
    )
    img = qrcode.make(otp_uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


# ROUTEs# 
@app.route("/")
def home():
    return render_template("home.html")

# ------------------------ REGISTER ------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="Username already exists")

        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        secret = pyotp.random_base32()

        new_user = User(username=username, password=hashed_pw, secret=secret)
        db.session.add(new_user)
        db.session.commit()

        qr_code = generate_qr_uri(username, secret)
        return render_template("qr.html", qr_code=qr_code, username=username)

    return render_template("register.html")

# ------------------------ LOGIN ------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if not user or not bcrypt.checkpw(password.encode(), user.password.encode()):
            return render_template("login.html", error="Invalid credentials")

        return render_template("verify.html", username=username)

    return render_template("login.html")

# ------------------------ VERIFY ------------------------
@app.route("/verify", methods=["POST"])
def verify():
    username = request.form["username"]
    token = request.form["token"]
    user = User.query.filter_by(username=username).first()

    if not user:
        return render_template("verify.html", username=username, error="User not found")

    totp = pyotp.TOTP(user.secret)
    if totp.verify(token):
        session["username"] = username
        session["user_id"] = user.id
        return redirect(url_for("dashboard"))
    else:
        return render_template("verify.html", username=username, error="Invalid token. Please try again.")

# ------------------------ DASHBOARD ------------------------
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    tokens = Token.query.filter_by(user_id=user_id).all()
    
    # Generate current codes for each token
    token_data = []
    for token in tokens:
        totp = pyotp.TOTP(token.secret)
        token_data.append({
            'id': token.id,
            'service': token.service,
            'code': totp.now()
        })

    return render_template("dashboard.html", username=session["username"], tokens=token_data)

# ------------------------ ADD TOKEN ------------------------
@app.route("/add_token", methods=["GET", "POST"])
def add_token():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        service = request.form["serviceName"]
        secret = pyotp.random_base32()
        user_id = session.get("user_id")

        new_token = Token(user_id=user_id, service=service, secret=secret)
        db.session.add(new_token)
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("addToken.html")

# ------------------------ DELETE TOKEN ------------------------
@app.route("/delete_token/<int:token_id>")
def delete_token(token_id):
    if "username" not in session:
        return redirect(url_for("login"))

    token = Token.query.get(token_id)
    if token and token.user_id == session.get("user_id"):
        db.session.delete(token)
        db.session.commit()

    return redirect(url_for("dashboard"))

# ------------------------ EXPORT TOKENS ------------------------
@app.route("/export_tokens")
def export_tokens():
    if "username" not in session:
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    tokens = Token.query.filter_by(user_id=user_id).all()

    export_data = []
    for token in tokens:
        export_data.append({
            "service": token.service,
            "secret": token.secret
        })

    return jsonify(export_data)

# ------------------------ IMPORT TOKENS ------------------------
@app.route("/import_token", methods=["GET", "POST"])
def import_token():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        backup_file = request.files["backup"]
        user_id = session.get("user_id")

        try:
            data = json.load(backup_file)
            for item in data:
                new_token = Token(
                    user_id=user_id,
                    service=item["service"],
                    secret=item["secret"]
                )
                db.session.add(new_token)
            db.session.commit()
            return redirect(url_for("dashboard"))
        except Exception as e:
            return render_template("importToken.html", error=f"Error importing: {str(e)}")

    return render_template("importToken.html")

# ------------------------ LOGOUT ------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)