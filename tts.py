import pyttsx3

def read_token(token):
    engine = pyttsx3.init()
    engine.say(f"Your code is {', '.join(token)}")
    engine.runAndWait()

    from tts import read_token

@app.route("/verify", methods=["POST"])
def verify():
    username = request.form["username"]
    token = request.form["token"]
    user = User.query.filter_by(username=username).first()

    if not user:
        return "User not found"

    totp = pyotp.TOTP(user.secret)
    if totp.verify(token):
        read_token(token)  ## Accessibility: read the code aloud ##
        session["username"] = username
        return redirect(url_for("dashboard"))
    else:
        return "Invalid token. Please try again."

