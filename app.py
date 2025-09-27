from flask import Flask, render_template, request
import bcrypt
import pyotp
import qrcode
import io
import base64

app = Flask(__name__)
users = {}

# Home route → show login form
@app.route("/")
def home():
    return render_template("login.html")


# Login route → handle form submission and registration
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = users.get(username)

        if not user:
            return "Invalid username"

        password_bytes = password.encode("utf-8")
        stored_hash = user["password"]

        # Check hashed password
        if not bcrypt.checkpw(password_bytes, stored_hash):
            return "Incorrect password"

        return render_template("verify.html", username=username)

    return render_template("login.html")


# Route to verify the 2FA token
@app.route("/verify", methods=["POST"])
def verify():
    username = request.form["username"]
    token = request.form["token"]

    user = users.get(username)
    if not user:
        return render_template("verify.html", message="❌ User not found", username=username)

    secret = user["secret"]
    totp = pyotp.TOTP(secret)

    if totp.verify(token):
        return render_template("success.html", message=f"✅ 2FA successful! Welcome, {username}")
    else:
        return render_template("verify.html", message="❌ Invalid token. Please try again.", username=username)


if __name__ == "__main__":
    app.run(debug=True)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Hash the password
        password_bytes = password.encode("utf-8")
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())

        # Generate TOTP secret
        totp = pyotp.TOTP(pyotp.random_base32())
        secret = totp.secret

        # Save user
        users[username] = {
            "password": hashed,
            "secret": secret
        }

        # Generate QR code
        uri = totp.provisioning_uri(name=username, issuer_name="MY2FAAPP")
        img = qrcode.make(uri)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode()

        return render_template("qr.html", username=username, qr_code=img_b64)

    return render_template("register.html")

@app.route("/")
def home():
    return render_template("home.html")

