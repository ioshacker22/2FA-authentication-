import os
import json
import pyotp
import qrcode
import logging
from io import BytesIO
from base64 import b64encode
from datetime import timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import bcrypt

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///2fa.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
    seconds=int(os.getenv('PERMANENT_SESSION_LIFETIME', 1800))
)
app.config['SESSION_COOKIE_HTTPONLY'] = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    secret = db.Column(db.String(32), nullable=False)
    tokens = db.relationship('Token', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    secret = db.Column(db.String(32), nullable=False)

    def __repr__(self):
        return f'<Token {self.service}>'

# Create tables
with app.app_context():
    db.create_all()

# Helper Functions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning(f'Unauthorized access attempt to {request.endpoint}')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number"
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter"
    return True, "Password is valid"

def validate_username(username):
    """Validate username"""
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    if len(username) > 20:
        return False, "Username must be less than 20 characters"
    if not username.isalnum():
        return False, "Username must contain only letters and numbers"
    return True, "Username is valid"

def sanitize_service_name(service):
    """Sanitize service name input"""
    return ''.join(char for char in service if char.isalnum() or char in ' -_').strip()[:100]

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            # Validate username
            valid, message = validate_username(username)
            if not valid:
                logger.warning(f'Registration failed: {message} for username {username}')
                return render_template('register.html', error=message)

            # Validate password
            valid, message = validate_password(password)
            if not valid:
                logger.warning(f'Registration failed: {message}')
                return render_template('register.html', error=message)

            # Check if user exists
            if User.query.filter_by(username=username).first():
                logger.warning(f'Registration failed: Username {username} already exists')
                return render_template('register.html', error='Username already exists')

            # Hash password and create secret
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            secret = pyotp.random_base32()

            # Create new user
            new_user = User(
                username=username,
                password=hashed_password.decode('utf-8'),
                secret=secret
            )
            db.session.add(new_user)
            db.session.commit()

            logger.info(f'New user registered: {username}')

            # Generate QR code
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=username,
                issuer_name='2FA-App'
            )
            
            img = qrcode.make(totp_uri)
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            qr_code = b64encode(buffered.getvalue()).decode('utf-8')

            session['temp_user_id'] = new_user.id
            return render_template('qr.html', qr_code=qr_code, username=username)

        except Exception as e:
            logger.error(f'Registration error: {str(e)}')
            db.session.rollback()
            return render_template('register.html', error='An error occurred during registration')

    return render_template('register.html')

@app.route('/verify', methods=['POST'])
@limiter.limit("10 per minute")
def verify():
    try:
        user_id = session.get('temp_user_id')
        if not user_id:
            return redirect(url_for('login'))

        code = request.form.get('code', '').strip()
        
        if not code.isdigit() or len(code) != 6:
            return render_template('verify.html', error='Invalid code format')

        user = User.query.get(user_id)
        if not user:
            return redirect(url_for('login'))

        totp = pyotp.TOTP(user.secret)
        if totp.verify(code, valid_window=1):
            session.pop('temp_user_id', None)
            session['user_id'] = user.id
            session.permanent = True
            logger.info(f'User verified and logged in: {user.username}')
            return redirect(url_for('dashboard'))
        else:
            logger.warning(f'Failed verification attempt for user: {user.username}')
            return render_template('verify.html', error='Invalid code')

    except Exception as e:
        logger.error(f'Verification error: {str(e)}')
        return render_template('verify.html', error='An error occurred during verification')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            code = request.form.get('code', '').strip()

            if not all([username, password, code]):
                return render_template('login.html', error='All fields are required')

            if not code.isdigit() or len(code) != 6:
                return render_template('login.html', error='Invalid code format')

            user = User.query.filter_by(username=username).first()
            
            if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
                logger.warning(f'Failed login attempt for username: {username}')
                return render_template('login.html', error='Invalid credentials')

            totp = pyotp.TOTP(user.secret)
            if totp.verify(code, valid_window=1):
                session['user_id'] = user.id
                session.permanent = True
                logger.info(f'User logged in: {username}')
                return redirect(url_for('dashboard'))
            else:
                logger.warning(f'Failed 2FA verification for user: {username}')
                return render_template('login.html', error='Invalid 2FA code')

        except Exception as e:
            logger.error(f'Login error: {str(e)}')
            return render_template('login.html', error='An error occurred during login')

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        user = User.query.get(session['user_id'])
        tokens = Token.query.filter_by(user_id=user.id).all()
        
        token_data = []
        for token in tokens:
            totp = pyotp.TOTP(token.secret)
            token_data.append({
                'id': token.id,
                'service': token.service,
                'code': totp.now()
            })
        
        return render_template('dashboard.html', username=user.username, tokens=token_data)
    except Exception as e:
        logger.error(f'Dashboard error: {str(e)}')
        return redirect(url_for('logout'))

@app.route('/add_token', methods=['GET', 'POST'])
@login_required
@limiter.limit("20 per hour")
def add_token():
    if request.method == 'POST':
        try:
            service = request.form.get('service', '').strip()
            
            if not service:
                return render_template('addToken.html', error='Service name is required')

            service = sanitize_service_name(service)
            
            if not service:
                return render_template('addToken.html', error='Invalid service name')

            # Check for duplicate service names
            existing = Token.query.filter_by(
                user_id=session['user_id'],
                service=service
            ).first()
            
            if existing:
                return render_template('addToken.html', error='Token for this service already exists')

            secret = pyotp.random_base32()
            new_token = Token(
                user_id=session['user_id'],
                service=service,
                secret=secret
            )
            db.session.add(new_token)
            db.session.commit()

            logger.info(f'Token added for service: {service} by user_id: {session["user_id"]}')
            return redirect(url_for('dashboard'))

        except Exception as e:
            logger.error(f'Add token error: {str(e)}')
            db.session.rollback()
            return render_template('addToken.html', error='An error occurred while adding token')

    return render_template('addToken.html')

@app.route('/delete_token/<int:token_id>')
@login_required
@limiter.limit("30 per hour")
def delete_token(token_id):
    try:
        token = Token.query.get_or_404(token_id)
        
        if token.user_id != session['user_id']:
            logger.warning(f'Unauthorized token deletion attempt by user_id: {session["user_id"]}')
            return redirect(url_for('dashboard'))

        service_name = token.service
        db.session.delete(token)
        db.session.commit()

        logger.info(f'Token deleted: {service_name} by user_id: {session["user_id"]}')
        return redirect(url_for('dashboard'))

    except Exception as e:
        logger.error(f'Delete token error: {str(e)}')
        db.session.rollback()
        return redirect(url_for('dashboard'))

@app.route('/export_tokens')
@login_required
@limiter.limit("10 per hour")
def export_tokens():
    try:
        tokens = Token.query.filter_by(user_id=session['user_id']).all()
        export_data = {
            'tokens': [
                {'service': token.service, 'secret': token.secret}
                for token in tokens
            ]
        }
        
        user = User.query.get(session['user_id'])
        logger.info(f'Tokens exported by user: {user.username}')
        
        return jsonify(export_data)

    except Exception as e:
        logger.error(f'Export tokens error: {str(e)}')
        return jsonify({'error': 'Export failed'}), 500

@app.route('/import_token', methods=['GET', 'POST'])
@login_required
@limiter.limit("10 per hour")
def import_token():
    if request.method == 'POST':
        try:
            file = request.files.get('file')
            
            if not file or not file.filename.endswith('.json'):
                return render_template('importToken.html', error='Please upload a valid JSON file')

            data = json.load(file)
            
            if 'tokens' not in data or not isinstance(data['tokens'], list):
                return render_template('importToken.html', error='Invalid file format')

            imported_count = 0
            for token_data in data['tokens']:
                service = sanitize_service_name(token_data.get('service', ''))
                secret = token_data.get('secret', '')
                
                if not service or not secret:
                    continue

                # Skip if token already exists
                existing = Token.query.filter_by(
                    user_id=session['user_id'],
                    service=service
                ).first()
                
                if existing:
                    continue

                new_token = Token(
                    user_id=session['user_id'],
                    service=service,
                    secret=secret
                )
                db.session.add(new_token)
                imported_count += 1

            db.session.commit()
            logger.info(f'{imported_count} tokens imported by user_id: {session["user_id"]}')
            
            return redirect(url_for('dashboard'))

        except json.JSONDecodeError:
            logger.error('Invalid JSON file uploaded')
            return render_template('importToken.html', error='Invalid JSON file')
        except Exception as e:
            logger.error(f'Import token error: {str(e)}')
            db.session.rollback()
            return render_template('importToken.html', error='An error occurred during import')

    return render_template('importToken.html')

@app.route('/logout')
@login_required
def logout():
    user_id = session.get('user_id')
    session.clear()
    logger.info(f'User logged out: user_id {user_id}')
    return redirect(url_for('home'))

@app.route('/health')
@csrf.exempt
def health():
    """Health check endpoint"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        logger.error(f'Health check failed: {str(e)}')
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('home.html'), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f'Rate limit exceeded: {request.remote_addr}')
    return "Rate limit exceeded. Please try again later.", 429

@app.errorhandler(500)
def internal_error(e):
    logger.error(f'Internal server error: {str(e)}')
    return "An internal error occurred. Please try again later.", 500

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)