"""
Database models for Main Lobby App
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model with subscription tier support"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Subscription tiers: 'free', 'tier1', 'tier2'
    subscription_tier = db.Column(db.String(20), default='free', nullable=False)
    stripe_customer_id = db.Column(db.String(100), unique=True, nullable=True)
    stripe_subscription_id = db.Column(db.String(100), unique=True, nullable=True)
    subscription_expires = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    donations = db.relationship('Donation', backref='user', lazy='dynamic')
    downloads = db.relationship('Download', backref='user', lazy='dynamic')

    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)

    def has_access_to_tier(self, required_tier):
        """Check if user's subscription allows access to content"""
        tier_hierarchy = {'free': 0, 'tier1': 1, 'tier2': 2}
        user_level = tier_hierarchy.get(self.subscription_tier, 0)
        required_level = tier_hierarchy.get(required_tier, 0)
        return user_level >= required_level

    def __repr__(self):
        return f'<User {self.username} ({self.subscription_tier})>'


class Content(db.Model):
    """Content model for music, videos, podcasts"""
    __tablename__ = 'content'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # Content types: 'music', 'video', 'podcast'
    content_type = db.Column(db.String(20), nullable=False, index=True)

    # Tier required: 'free', 'tier1', 'tier2'
    tier_required = db.Column(db.String(20), default='free', nullable=False, index=True)

    # Flags
    is_new_release = db.Column(db.Boolean, default=False)
    is_exclusive = db.Column(db.Boolean, default=False)
    is_downloadable = db.Column(db.Boolean, default=False)

    # File paths
    file_path = db.Column(db.String(500), nullable=False)  # Main file (audio/video)
    thumbnail_path = db.Column(db.String(500), nullable=True)

    # Metadata
    duration_seconds = db.Column(db.Integer, nullable=True)
    file_size_bytes = db.Column(db.BigInteger, nullable=True)

    release_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    downloads = db.relationship('Download', backref='content', lazy='dynamic')

    def __repr__(self):
        return f'<Content {self.title} ({self.content_type}, {self.tier_required})>'


class Donation(db.Model):
    """Donation tracking"""
    __tablename__ = 'donations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    amount = db.Column(db.Float, nullable=False)  # Amount in USD
    currency = db.Column(db.String(3), default='USD', nullable=False)
    message = db.Column(db.Text, nullable=True)

    # Payment info
    stripe_payment_intent_id = db.Column(db.String(100), unique=True, nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, completed, failed

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Donation ${self.amount} from User {self.user_id}>'


class Download(db.Model):
    """Track user downloads for analytics and limits"""
    __tablename__ = 'downloads'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)

    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv6

    def __repr__(self):
        return f'<Download User {self.user_id} -> Content {self.content_id}>'


class Payment(db.Model):
    """Payment history for subscriptions and donations"""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD', nullable=False)

    # Payment types: 'subscription', 'donation'
    payment_type = db.Column(db.String(20), nullable=False)

    # Stripe IDs
    stripe_payment_intent_id = db.Column(db.String(100), unique=True, nullable=True)
    stripe_invoice_id = db.Column(db.String(100), nullable=True)

    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, completed, failed, refunded

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Payment ${self.amount} ({self.payment_type}) - {self.status}>'
