# 2FA Authentication App

A secure Flask-based Two-Factor Authentication (2FA) application with TOTP token management, rate limiting, and production-ready features.

## 🚀 Features

* 🔐 **Secure Authentication** - Bcrypt password hashing with strong password requirements
* 📱 **QR Code Generation** - Easy authenticator app setup
* 🔑 **Multi-Service TOTP** - Manage 2FA tokens for multiple services
* 💾 **Import/Export** - Backup and restore tokens as JSON
* 🎨 **Modern UI** - Responsive design with glassmorphism effects
* 🛡️ **Security Features**:
  - CSRF protection
  - Rate limiting on critical endpoints
  - Session management with timeout
  - Input validation and sanitization
  - Secure password requirements
  - Logging for security events
* 📦 **Production Ready** - Docker support, health checks, environment configuration

## 📋 Prerequisites

* Python 3.8 or higher
* pip (Python package manager)
* (Optional) Docker and Docker Compose

## 🔧 Installation

### Option 1: Standard Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ioshacker22/2FA-authentication-.git
   cd 2FA-authentication-
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and set your SECRET_KEY
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the app**
   ```
   http://127.0.0.1:5000
   ```

### Option 2: Docker Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ioshacker22/2FA-authentication-.git
   cd 2FA-authentication-
   ```

2. **Set environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and set your SECRET_KEY
   ```

3. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Access the app**
   ```
   http://localhost:5000
   ```

## 🔒 Security Features

### Password Requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

### Rate Limiting
- Registration: 5 per hour
- Login: 10 per minute
- Token operations: 20-30 per hour
- Global: 200 per day, 50 per hour

### Session Security
- HTTP-only cookies
- 30-minute session timeout
- Secure cookies in production (HTTPS)
- CSRF protection on all forms

## 📁 Project Structure

```
2FA-authentication-/
├── app.py                 # Main application with security improvements
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose setup
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── templates/
│   ├── home.html
│   ├── register.html
│   ├── login.html
│   ├── verify.html
│   ├── qr.html
│   ├── dashboard.html
│   ├── addToken.html
│   └── importToken.html
├── static/
│   └── style.css
└── instance/             # Database and logs (gitignored)
    └── 2fa.db
```

## 🔐 Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Required for production
SECRET_KEY=your-super-secret-key-min-32-characters

# Optional - defaults provided
FLASK_ENV=production
DATABASE_URL=sqlite:///2fa.db
SESSION_COOKIE_SECURE=True
PERMANENT_SESSION_LIFETIME=1800
```

## 🚀 Production Deployment

### Important Production Settings

1. **Generate a strong SECRET_KEY**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Update .env file**
   ```bash
   SECRET_KEY=<generated-key-from-step-1>
   FLASK_ENV=production
   FLASK_DEBUG=False
   SESSION_COOKIE_SECURE=True
   ```

3. **Use a production database**
   ```bash
   # PostgreSQL example
   DATABASE_URL=postgresql://user:password@localhost/dbname
   ```

4. **Run with production server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

5. **Use HTTPS** (required for secure cookies)
   - Use nginx or Apache as reverse proxy
   - Configure SSL certificates (Let's Encrypt recommended)

6. **Enable proper logging**
   ```bash
   mkdir logs
   # Logs are automatically written to app.log
   ```

### Docker Production Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📖 Usage Guide

### First Time Setup

1. **Register an account**
   - Click "Register" on home page
   - Enter username (3-20 alphanumeric characters)
   - Enter strong password (meets all requirements)
   - Scan QR code with authenticator app
   - Enter 6-digit verification code

2. **Login**
   - Enter username and password
   - Enter current 6-digit code from authenticator app

### Managing Tokens

#### Add Token
1. Click "Add Token" on dashboard
2. Enter service name (e.g., "GitHub", "Gmail")
3. New TOTP token generated automatically

#### View Codes
- Dashboard displays all tokens with current codes
- Codes refresh every 30 seconds

#### Export Tokens
1. Click "Export" button
2. Save JSON file securely
3. Use for backup or migration

#### Import Tokens
1. Click "Import" button
2. Upload previously exported JSON file
3. Tokens are restored to your account

#### Delete Token
1. Click "Delete" next to any token
2. Token is permanently removed

## 🛠️ API Endpoints

| Endpoint | Method | Rate Limit | Description |
|----------|--------|------------|-------------|
| `/` | GET | - | Home page |
| `/register` | GET, POST | 5/hour | User registration |
| `/login` | GET, POST | 10/min | User login |
| `/verify` | POST | 10/min | 2FA verification |
| `/dashboard` | GET | - | User dashboard |
| `/add_token` | GET, POST | 20/hour | Add new token |
| `/delete_token/<id>` | GET | 30/hour | Delete token |
| `/export_tokens` | GET | 10/hour | Export as JSON |
| `/import_token` | GET, POST | 10/hour | Import from JSON |
| `/logout` | GET | - | Logout |
| `/health` | GET | - | Health check |

## 🐛 Troubleshooting

### Common Issues

**Module not found errors**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Port already in use**
```bash
# Change port in app.py or use environment variable
export FLASK_RUN_PORT=5001
python app.py
```

**Database locked errors**
```bash
# Stop all instances and restart
pkill -f app.py
python app.py
```

**Rate limit errors**
- Wait for the specified time period
- Check if you're being rate limited incorrectly
- Review logs in `app.log`

### Development Mode

To run in development mode with auto-reload:

```bash
export FLASK_ENV=development
export FLASK_DEBUG=True
python app.py
```

## 📊 Logging

Application logs are written to `app.log` with the following information:
- User registration and login events
- Token operations (add, delete, import, export)
- Security events (failed logins, rate limits)
- Errors and exceptions

View logs:
```bash
tail -f app.log
```

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-flask

# Run tests (if test suite exists)
pytest
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

* Flask framework
* PyOTP for TOTP implementation
* QRCode library
* Bcrypt for password hashing
* Flask-Limiter for rate limiting
* Flask-WTF for CSRF protection

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing issues and documentation
- Review logs for error details

## 🗺️ Roadmap

- [x] User authentication with 2FA
- [x] TOTP token management
- [x] Import/Export functionality
- [x] Rate limiting
- [x] CSRF protection
- [x] Docker support
- [ ] Backup codes for recovery
- [ ] Email verification
- [ ] WebAuthn/U2F support
- [ ] Mobile app
- [ ] Account activity log
- [ ] Multi-language support

---

**Built with ❤️ using Flask | Secure by Design**
