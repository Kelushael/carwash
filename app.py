"""
Main Lobby App - Spotify-style platform with tiered subscriptions
"""
import os
from flask import Flask, render_template, jsonify, request, send_file, abort
from flask_login import current_user, login_required
from models import db, User, Content, Donation, Download, Payment
from auth import auth_bp, init_auth, tier_required
from datetime import datetime
from werkzeug.utils import secure_filename

# Create Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///mainlobby.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload

# Stripe configuration
app.config['STRIPE_PUBLIC_KEY'] = os.environ.get('STRIPE_PUBLIC_KEY', '')
app.config['STRIPE_SECRET_KEY'] = os.environ.get('STRIPE_SECRET_KEY', '')

# Subscription tier pricing (monthly)
TIER_PRICING = {
    'tier1': {'price': 3, 'name': 'Tier 1', 'features': ['New releases', 'Exclusive drops', 'Downloadable content']},
    'tier2': {'price': 12, 'name': 'Tier 2', 'features': ['Everything in Tier 1', 'Music videos', 'Podcasts', 'Early access']}
}

# Initialize extensions
db.init_app(app)
init_auth(app)

# Register blueprints
app.register_blueprint(auth_bp)


# Main routes

@app.route('/')
def index():
    """Home page - show new releases based on user tier"""
    # Get new releases
    query = Content.query.filter_by(is_new_release=True).order_by(Content.release_date.desc())

    # Filter by tier access if logged in
    if current_user.is_authenticated:
        user_tier = current_user.subscription_tier
    else:
        user_tier = 'free'

    # Show content user has access to
    tier_hierarchy = {'free': ['free'], 'tier1': ['free', 'tier1'], 'tier2': ['free', 'tier1', 'tier2']}
    accessible_tiers = tier_hierarchy.get(user_tier, ['free'])

    new_releases = query.filter(Content.tier_required.in_(accessible_tiers)).limit(20).all()

    return render_template('index.html', new_releases=new_releases, tier_pricing=TIER_PRICING)


@app.route('/browse')
def browse():
    """Browse all content"""
    content_type = request.args.get('type', 'all')
    tier = request.args.get('tier', 'all')

    query = Content.query

    # Filter by content type
    if content_type != 'all':
        query = query.filter_by(content_type=content_type)

    # Filter by user's accessible tiers
    if current_user.is_authenticated:
        user_tier = current_user.subscription_tier
    else:
        user_tier = 'free'

    tier_hierarchy = {'free': ['free'], 'tier1': ['free', 'tier1'], 'tier2': ['free', 'tier1', 'tier2']}
    accessible_tiers = tier_hierarchy.get(user_tier, ['free'])

    if tier != 'all':
        if tier in accessible_tiers:
            query = query.filter_by(tier_required=tier)
        else:
            # User trying to view tier they don't have access to - show as locked
            pass

    content = query.order_by(Content.release_date.desc()).all()

    return render_template('browse.html', content=content, content_type=content_type, tier=tier)


@app.route('/content/<int:content_id>')
def content_detail(content_id):
    """View individual content item"""
    content = Content.query.get_or_404(content_id)

    # Check tier access
    has_access = False
    if current_user.is_authenticated:
        has_access = current_user.has_access_to_tier(content.tier_required)
    else:
        has_access = content.tier_required == 'free'

    return render_template('content_detail.html', content=content, has_access=has_access)


@app.route('/stream/<int:content_id>')
def stream_content(content_id):
    """Stream audio/video content"""
    content = Content.query.get_or_404(content_id)

    # Check tier access
    has_access = False
    if current_user.is_authenticated:
        has_access = current_user.has_access_to_tier(content.tier_required)
    else:
        has_access = content.tier_required == 'free'

    if not has_access:
        abort(403, description='Subscription tier required to access this content')

    # Serve file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], content.file_path)
    if not os.path.exists(file_path):
        abort(404, description='Content file not found')

    return send_file(file_path)


@app.route('/download/<int:content_id>')
@login_required
@tier_required('tier1')
def download_content(content_id):
    """Download content (Tier 1+ only)"""
    content = Content.query.get_or_404(content_id)

    # Check if downloadable
    if not content.is_downloadable:
        abort(403, description='This content is not available for download')

    # Check tier access
    if not current_user.has_access_to_tier(content.tier_required):
        abort(403, description='Subscription tier required to access this content')

    # Track download
    download = Download(
        user_id=current_user.id,
        content_id=content.id,
        ip_address=request.remote_addr
    )
    db.session.add(download)
    db.session.commit()

    # Serve file for download
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], content.file_path)
    if not os.path.exists(file_path):
        abort(404, description='Content file not found')

    return send_file(file_path, as_attachment=True, download_name=f"{content.title}.{content.file_path.split('.')[-1]}")


@app.route('/pricing')
def pricing():
    """Pricing and subscription tiers page"""
    return render_template('pricing.html', tier_pricing=TIER_PRICING)


@app.route('/donate')
def donate():
    """Donations page"""
    return render_template('donate.html', stripe_public_key=app.config['STRIPE_PUBLIC_KEY'])


@app.route('/api/donate', methods=['POST'])
def process_donation():
    """Process donation payment"""
    data = request.get_json()

    amount = data.get('amount')
    message = data.get('message', '')

    if not amount or amount <= 0:
        return jsonify({'error': 'Invalid donation amount'}), 400

    # TODO: Integrate Stripe payment processing here
    # For now, create pending donation

    donation = Donation(
        user_id=current_user.id if current_user.is_authenticated else None,
        amount=amount,
        message=message,
        status='pending'
    )
    db.session.add(donation)
    db.session.commit()

    return jsonify({
        'message': 'Donation received! Thank you for your support.',
        'donation_id': donation.id
    }), 200


@app.route('/api/subscribe/<tier>', methods=['POST'])
@login_required
def subscribe(tier):
    """Subscribe to a tier"""
    if tier not in TIER_PRICING:
        return jsonify({'error': 'Invalid subscription tier'}), 400

    # TODO: Integrate Stripe subscription here
    # For now, just update user tier (for development)

    current_user.subscription_tier = tier
    db.session.commit()

    return jsonify({
        'message': f'Successfully subscribed to {TIER_PRICING[tier]["name"]}',
        'tier': tier
    }), 200


# API Routes for content

@app.route('/api/content', methods=['GET'])
def api_get_content():
    """Get content list (API)"""
    content_type = request.args.get('type', 'all')
    tier = request.args.get('tier', 'all')
    new_only = request.args.get('new_only', 'false').lower() == 'true'
    exclusive_only = request.args.get('exclusive_only', 'false').lower() == 'true'

    query = Content.query

    if content_type != 'all':
        query = query.filter_by(content_type=content_type)

    if tier != 'all':
        query = query.filter_by(tier_required=tier)

    if new_only:
        query = query.filter_by(is_new_release=True)

    if exclusive_only:
        query = query.filter_by(is_exclusive=True)

    content = query.order_by(Content.release_date.desc()).all()

    return jsonify([{
        'id': c.id,
        'title': c.title,
        'artist': c.artist,
        'description': c.description,
        'content_type': c.content_type,
        'tier_required': c.tier_required,
        'is_new_release': c.is_new_release,
        'is_exclusive': c.is_exclusive,
        'is_downloadable': c.is_downloadable,
        'duration_seconds': c.duration_seconds,
        'release_date': c.release_date.isoformat(),
        'thumbnail_url': f'/uploads/{c.thumbnail_path}' if c.thumbnail_path else None
    } for c in content]), 200


# Admin routes (simple content upload)

@app.route('/admin/upload', methods=['GET', 'POST'])
@login_required
def admin_upload():
    """Upload content (admin only - add proper auth later)"""
    if request.method == 'GET':
        return render_template('admin_upload.html')

    # Handle file upload
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Save file
    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Get file size
    file_size = os.path.getsize(file_path)

    # Create content entry
    content = Content(
        title=request.form.get('title', filename),
        artist=request.form.get('artist', ''),
        description=request.form.get('description', ''),
        content_type=request.form.get('content_type', 'music'),
        tier_required=request.form.get('tier_required', 'free'),
        is_new_release=request.form.get('is_new_release', 'false').lower() == 'true',
        is_exclusive=request.form.get('is_exclusive', 'false').lower() == 'true',
        is_downloadable=request.form.get('is_downloadable', 'false').lower() == 'true',
        file_path=filename,
        file_size_bytes=file_size
    )

    db.session.add(content)
    db.session.commit()

    return jsonify({
        'message': 'Content uploaded successfully',
        'content_id': content.id
    }), 201


# Database initialization

@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()
    print('Database initialized successfully!')


@app.cli.command()
def seed_db():
    """Seed database with sample data"""
    # Create sample user
    user = User(email='test@example.com', username='testuser')
    user.set_password('password123')
    db.session.add(user)

    # Create sample content
    sample_content = [
        Content(
            title='Summer Vibes',
            artist='DJ Cool',
            description='Chill summer beats',
            content_type='music',
            tier_required='free',
            is_new_release=True,
            file_path='sample1.mp3'
        ),
        Content(
            title='Exclusive Drop',
            artist='Artist X',
            description='Exclusive release for tier 1 members',
            content_type='music',
            tier_required='tier1',
            is_new_release=True,
            is_exclusive=True,
            is_downloadable=True,
            file_path='sample2.mp3'
        ),
        Content(
            title='Behind the Scenes',
            artist='Artist X',
            description='Music video - tier 2 exclusive',
            content_type='video',
            tier_required='tier2',
            is_new_release=True,
            file_path='sample_video.mp4'
        )
    ]

    for content in sample_content:
        db.session.add(content)

    db.session.commit()
    print('Database seeded with sample data!')


if __name__ == '__main__':
    # Create upload folder
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Run app
    app.run(host='0.0.0.0', port=5000, debug=True)
