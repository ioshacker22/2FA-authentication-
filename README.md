# 2FA Authentication App

A Flask-based Two-Factor Authentication (2FA) application that allows users to manage TOTP (Time-based One-Time Password) tokens for multiple services.

## Features

- 🔐 **User Registration & Login** with password hashing
- 📱 **QR Code Generation** for easy authenticator app setup
- 🔑 **TOTP Token Management** - Add, view, and delete 2FA tokens for multiple services
- 💾 **Import/Export** - Backup and restore your tokens as JSON
- 🎨 **Modern UI** - Clean, responsive design with glassmorphism effects
- 🔒 **Secure** - Bcrypt password hashing and session management

## Screenshots

```
Home Page → Register → QR Code Scan → Dashboard with Tokens
```

## Tech Stack

- **Backend**: Flask, SQLAlchemy
- **Security**: Bcrypt, PyOTP
- **Database**: SQLite
- **Frontend**: HTML5, CSS3
- **Libraries**: QRCode, Pillow

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone or download the repository**
   ```bash
   git clone <your-repo-url>
   cd 2FA-authentication-Minty
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install flask flask-sqlalchemy pyotp qrcode bcrypt pillow
   ```

4. **Project structure should look like this:**
   ```
   2FA-authentication-Minty/
   ├── app.py
   ├── templates/
   │   ├── home.html
   │   ├── register.html
   │   ├── login.html
   │   ├── verify.html
   │   ├── qr.html
   │   ├── dashboard.html
   │   ├── addToken.html
   │   └── importToken.html
   └── static/
       └── style.css
   ```

5. **Run the application**
   ```bash
   python3 app.py
   ```

6. **Open your browser**
   ```
   http://127.0.0.1:5000
   ```

## Usage

### First Time Registration

1. Click **Register** on the home page
2. Enter a username and password
3. Scan the QR code with your authenticator app:
   - Google Authenticator
   - Microsoft Authenticator
   - Authy
   - Any TOTP-compatible app
4. Enter the 6-digit code from your app
5. You're logged in!

### Login

1. Click **Login**
2. Enter your credentials
3. Enter the current 6-digit code from your authenticator app
4. Access your dashboard

### Managing Tokens

#### Add a Token
- Click **Add Token** on the dashboard
- Enter the service name (e.g., "GitHub", "Gmail")
- A new TOTP token will be generated

#### View Current Codes
- All your tokens are displayed on the dashboard
- Codes refresh every 30 seconds automatically

#### Export Tokens (Backup)
- Click **Export** to download a JSON file
- Save this file securely for backup purposes

#### Import Tokens (Restore)
- Click **Import**
- Upload a previously exported JSON file
- All tokens will be restored

#### Delete a Token
- Click **Delete** next to any token
- Confirm the deletion

## Security Considerations

### For Development
- Uses SQLite database (`2fa.db`)
- Debug mode is enabled
- Secret key can be default

### For Production Deployment

⚠️ **Important: Do NOT deploy with default settings**

1. **Set a strong SECRET_KEY**
   ```bash
   export SECRET_KEY="your-very-strong-random-secret-key-here"
   ```

2. **Disable debug mode** in `app.py`:
   ```python
   app.run(debug=False)
   ```

3. **Use a production WSGI server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 app:app
   ```

4. **Use HTTPS** - Never serve over plain HTTP in production

5. **Use a production database**
   - PostgreSQL or MySQL instead of SQLite
   - Update `SQLALCHEMY_DATABASE_URI` in `app.py`

6. **Add additional security**
   - CSRF protection (Flask-WTF)
   - Rate limiting (Flask-Limiter)
   - Input validation
   - Security headers

7. **Environment variables**
   ```bash
   export SECRET_KEY="your-secret-key"
   export DATABASE_URL="postgresql://user:pass@localhost/dbname"
   ```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page |
| `/register` | GET, POST | User registration |
| `/login` | GET, POST | User login |
| `/verify` | POST | 2FA verification |
| `/dashboard` | GET | User dashboard |
| `/add_token` | GET, POST | Add new token |
| `/delete_token/<id>` | GET | Delete token |
| `/export_tokens` | GET | Export tokens as JSON |
| `/import_token` | GET, POST | Import tokens from JSON |
| `/logout` | GET | Logout user |

## Database Schema

### User Table
- `id` - Primary key
- `username` - Unique username
- `password` - Bcrypt hashed password
- `secret` - Base32 TOTP secret

### Token Table
- `id` - Primary key
- `user_id` - Foreign key to User
- `service` - Service name
- `secret` - Base32 TOTP secret

## Troubleshooting

### Module Not Found Errors
```bash
pip install --upgrade pip
pip install flask flask-sqlalchemy pyotp qrcode bcrypt pillow
```

### Port Already in Use
Edit `app.py` and change the port:
```python
app.run(debug=True, port=5001)
```

### Database Issues
Delete the database and restart:
```bash
rm 2fa.db
python3 app.py
```

### QR Code Not Displaying
- Check that Pillow is installed: `pip install pillow`
- Verify the `static/` folder exists

## Dependencies

```
Flask>=2.3.0
Flask-SQLAlchemy>=3.0.0
pyotp>=2.9.0
qrcode>=7.4.0
bcrypt>=4.0.0
Pillow>=10.0.0
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Flask framework for the web application
- PyOTP for TOTP implementation
- QRCode library for QR code generation
- Bcrypt for secure password hashing

## Support

If you encounter any issues or have questions:
1. Check the Troubleshooting section
2. Open an issue on GitHub
3. Review the Flask documentation: https://flask.palletsprojects.com/

## Roadmap

- [ ] Add backup codes for account recovery
- [ ] Implement email verification
- [ ] Add support for U2F/WebAuthn
- [ ] Mobile-responsive improvements
- [ ] Dark/Light theme toggle
- [ ] Multi-language support
- [ ] Password strength meter
- [ ] Account activity log

---

**Made with ❤️ using Flask**
