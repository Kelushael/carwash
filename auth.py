"""
Authentication module for Main Lobby App
"""
from functools import wraps
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
login_manager = LoginManager()


def init_auth(app):
    """Initialize authentication for the app"""
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))


def tier_required(required_tier):
    """Decorator to restrict access based on subscription tier"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.has_access_to_tier(required_tier):
                if request.is_json:
                    return jsonify({'error': 'Subscription tier required', 'required_tier': required_tier}), 403
                flash(f'You need {required_tier} subscription to access this content.', 'error')
                return redirect(url_for('main.pricing'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# API Routes

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('main.index'))
        return render_template('register.html')

    # Handle POST - API and form both
    data = request.get_json() if request.is_json else request.form

    email = data.get('email', '').strip().lower()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    # Validation
    errors = []
    if not email or '@' not in email:
        errors.append('Valid email is required')
    if not username or len(username) < 3:
        errors.append('Username must be at least 3 characters')
    if not password or len(password) < 6:
        errors.append('Password must be at least 6 characters')
    if password != confirm_password:
        errors.append('Passwords do not match')

    # Check if user exists
    if User.query.filter_by(email=email).first():
        errors.append('Email already registered')
    if User.query.filter_by(username=username).first():
        errors.append('Username already taken')

    if errors:
        if request.is_json:
            return jsonify({'error': errors}), 400
        for error in errors:
            flash(error, 'error')
        return render_template('register.html'), 400

    # Create user
    user = User(email=email, username=username)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    # Auto login after registration
    login_user(user)

    if request.is_json:
        return jsonify({
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'subscription_tier': user.subscription_tier
            }
        }), 201

    flash('Registration successful! Welcome to Main Lobby.', 'success')
    return redirect(url_for('main.index'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('main.index'))
        return render_template('login.html')

    # Handle POST
    data = request.get_json() if request.is_json else request.form

    email_or_username = data.get('email', '').strip().lower()
    password = data.get('password', '')
    remember = data.get('remember', False)

    if not email_or_username or not password:
        error = 'Email/username and password are required'
        if request.is_json:
            return jsonify({'error': error}), 400
        flash(error, 'error')
        return render_template('login.html'), 400

    # Find user by email or username
    user = User.query.filter(
        (User.email == email_or_username) | (User.username == email_or_username)
    ).first()

    if not user or not user.check_password(password):
        error = 'Invalid credentials'
        if request.is_json:
            return jsonify({'error': error}), 401
        flash(error, 'error')
        return render_template('login.html'), 401

    login_user(user, remember=remember)

    if request.is_json:
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'subscription_tier': user.subscription_tier
            }
        }), 200

    flash(f'Welcome back, {user.username}!', 'success')
    next_page = request.args.get('next')
    return redirect(next_page or url_for('main.index'))


@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """User logout"""
    logout_user()

    if request.is_json:
        return jsonify({'message': 'Logged out successfully'}), 200

    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info"""
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'username': current_user.username,
        'subscription_tier': current_user.subscription_tier,
        'subscription_expires': current_user.subscription_expires.isoformat() if current_user.subscription_expires else None,
        'created_at': current_user.created_at.isoformat()
    }), 200


@auth_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    data = request.get_json() if request.is_json else request.form

    username = data.get('username', '').strip()
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    errors = []

    # Update username
    if username and username != current_user.username:
        if len(username) < 3:
            errors.append('Username must be at least 3 characters')
        elif User.query.filter_by(username=username).first():
            errors.append('Username already taken')
        else:
            current_user.username = username

    # Update password
    if new_password:
        if not current_password:
            errors.append('Current password required to set new password')
        elif not current_user.check_password(current_password):
            errors.append('Current password is incorrect')
        elif len(new_password) < 6:
            errors.append('New password must be at least 6 characters')
        else:
            current_user.set_password(new_password)

    if errors:
        if request.is_json:
            return jsonify({'error': errors}), 400
        for error in errors:
            flash(error, 'error')
        return redirect(url_for('auth.profile'))

    db.session.commit()

    if request.is_json:
        return jsonify({'message': 'Profile updated successfully'}), 200

    flash('Profile updated successfully!', 'success')
    return redirect(url_for('auth.profile'))


@auth_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html', user=current_user)
