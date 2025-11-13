#!/usr/bin/env python3
"""
Car Wash Mixer - Main Web Application
Professional stem separation with tiered subscriptions
"""

from flask import Flask, render_template, request, jsonify, session, send_file, url_for
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import uuid
import json
from datetime import datetime, timedelta
import threading
import queue

# Import stem separation
import torch
import numpy as np
import soundfile as sf
from demucs.pretrained import get_model
from demucs.apply import apply_model
from demucs.audio import save_audio, convert_audio

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max file size
app.config['UPLOAD_FOLDER'] = Path('uploads')
app.config['OUTPUT_FOLDER'] = Path('outputs')

# Ensure folders exist
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['OUTPUT_FOLDER'].mkdir(exist_ok=True)

# In-memory storage (in production, use a database)
users_db = {}
processing_queue = queue.Queue()
processing_status = {}

# Subscription tiers configuration
SUBSCRIPTION_TIERS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'monthly_limit': 2,
        'stems': 2,  # vocals + instrumental only
        'stem_types': ['vocals', 'instrumental'],
        'priority': 3,
        'batch_upload': False,
        'features': [
            '2 songs per month',
            'Basic 2-stem separation',
            'Vocals + Instrumental',
            'Standard processing speed'
        ]
    },
    'pro': {
        'name': 'Pro',
        'price': 9.99,
        'monthly_limit': 20,
        'stems': 4,
        'stem_types': ['vocals', 'drums', 'bass', 'other'],
        'priority': 2,
        'batch_upload': False,
        'features': [
            '20 songs per month',
            'Full 4-stem separation',
            'Vocals, Drums, Bass, Other',
            'Priority processing',
            'High-quality exports'
        ]
    },
    'premium': {
        'name': 'Premium',
        'price': 29.99,
        'monthly_limit': -1,  # unlimited
        'stems': 4,
        'stem_types': ['vocals', 'drums', 'bass', 'other'],
        'priority': 1,
        'batch_upload': True,
        'features': [
            'Unlimited songs',
            'Full 4-stem separation',
            'Fastest processing',
            'Batch upload',
            'Premium support',
            'API access'
        ]
    }
}

# Load Demucs model
demucs_model = None
model_lock = threading.Lock()


def init_model():
    """Initialize Demucs model"""
    global demucs_model
    with model_lock:
        if demucs_model is None:
            print("Loading Demucs model...")
            demucs_model = get_model('htdemucs')
            demucs_model.cpu()
            demucs_model.eval()
            print("Model loaded successfully!")


# Start model loading in background
threading.Thread(target=init_model, daemon=True).start()


def get_user_session():
    """Get or create user session"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        session['tier'] = 'free'
        session['created_at'] = datetime.now().isoformat()

        # Initialize user in database
        users_db[session['user_id']] = {
            'id': session['user_id'],
            'tier': 'free',
            'monthly_usage': 0,
            'total_processed': 0,
            'last_reset': datetime.now().isoformat(),
            'history': []
        }

    return users_db.get(session['user_id'])


def check_usage_limit(user):
    """Check if user has exceeded monthly limit"""
    tier = SUBSCRIPTION_TIERS[user['tier']]

    # Reset monthly counter if needed
    last_reset = datetime.fromisoformat(user['last_reset'])
    if datetime.now() - last_reset > timedelta(days=30):
        user['monthly_usage'] = 0
        user['last_reset'] = datetime.now().isoformat()

    # Check limit
    if tier['monthly_limit'] == -1:  # unlimited
        return True

    return user['monthly_usage'] < tier['monthly_limit']


def separate_stems_demucs(input_path, output_dir, tier='free'):
    """Separate audio into stems using Demucs"""
    try:
        # Load audio
        wav, sr = sf.read(input_path)

        # Convert to torch tensor
        if len(wav.shape) == 1:
            wav = np.stack([wav, wav], axis=1)

        wav_tensor = torch.from_numpy(wav.T).float()

        # Convert to model sample rate
        if sr != demucs_model.samplerate:
            wav_tensor = convert_audio(wav_tensor, sr, demucs_model.samplerate,
                                      demucs_model.audio_channels)

        sample_rate = demucs_model.samplerate

        # Apply model
        with torch.no_grad():
            sources = apply_model(demucs_model, wav_tensor.unsqueeze(0), device='cpu')[0]

        sources_np = sources.cpu().numpy()

        # Extract stems based on tier
        tier_config = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])

        if tier_config['stems'] == 2:
            # Free tier: combine into vocals and instrumental
            vocals = sources_np[3]  # vocals
            instrumental = sources_np[0] + sources_np[1] + sources_np[2]  # drums + bass + other

            stems = {
                'vocals': vocals,
                'instrumental': instrumental
            }
        else:
            # Pro/Premium tier: all 4 stems
            stems = {
                'drums': sources_np[0],
                'bass': sources_np[1],
                'other': sources_np[2],
                'vocals': sources_np[3]
            }

        # Save stems
        output_paths = {}
        for stem_name, stem_audio in stems.items():
            stem_path = output_dir / f"{stem_name}.wav"
            save_audio(torch.from_numpy(stem_audio), str(stem_path), sample_rate)
            output_paths[stem_name] = str(stem_path)

        return {
            'success': True,
            'stems': output_paths,
            'sample_rate': sample_rate
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def process_worker():
    """Background worker for processing queue"""
    while True:
        try:
            job = processing_queue.get()
            if job is None:
                break

            job_id = job['id']
            processing_status[job_id]['status'] = 'processing'

            # Perform separation
            result = separate_stems_demucs(
                job['input_path'],
                job['output_dir'],
                job['tier']
            )

            if result['success']:
                processing_status[job_id]['status'] = 'completed'
                processing_status[job_id]['stems'] = result['stems']
            else:
                processing_status[job_id]['status'] = 'failed'
                processing_status[job_id]['error'] = result['error']

            processing_queue.task_done()

        except Exception as e:
            print(f"Worker error: {e}")


# Start processing worker
processing_thread = threading.Thread(target=process_worker, daemon=True)
processing_thread.start()


@app.route('/')
def index():
    """Main lobby page"""
    user = get_user_session()
    tier_info = SUBSCRIPTION_TIERS[user['tier']]

    # Calculate remaining songs
    remaining = tier_info['monthly_limit'] - user['monthly_usage']
    if tier_info['monthly_limit'] == -1:
        remaining = -1  # unlimited

    return render_template('lobby.html',
                         user=user,
                         tier=user['tier'],
                         tier_info=tier_info,
                         remaining=remaining,
                         all_tiers=SUBSCRIPTION_TIERS)


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    user = get_user_session()

    # Check usage limit
    if not check_usage_limit(user):
        return jsonify({
            'success': False,
            'error': 'Monthly limit reached. Please upgrade your plan.'
        }), 403

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    # Check file extension
    allowed_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        return jsonify({
            'success': False,
            'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
        }), 400

    # Save file
    filename = secure_filename(file.filename)
    job_id = str(uuid.uuid4())
    upload_dir = app.config['UPLOAD_FOLDER'] / job_id
    output_dir = app.config['OUTPUT_FOLDER'] / job_id
    upload_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    input_path = upload_dir / filename
    file.save(input_path)

    # Create job
    job = {
        'id': job_id,
        'user_id': user['id'],
        'filename': filename,
        'input_path': input_path,
        'output_dir': output_dir,
        'tier': user['tier'],
        'created_at': datetime.now().isoformat()
    }

    processing_status[job_id] = {
        'status': 'queued',
        'filename': filename,
        'created_at': job['created_at']
    }

    # Add to queue
    processing_queue.put(job)

    # Update usage
    user['monthly_usage'] += 1
    user['total_processed'] += 1
    user['history'].append({
        'job_id': job_id,
        'filename': filename,
        'timestamp': job['created_at']
    })

    return jsonify({
        'success': True,
        'job_id': job_id,
        'filename': filename
    })


@app.route('/status/<job_id>')
def get_status(job_id):
    """Get processing status"""
    if job_id not in processing_status:
        return jsonify({'success': False, 'error': 'Job not found'}), 404

    status = processing_status[job_id]
    return jsonify({
        'success': True,
        'status': status['status'],
        'filename': status['filename'],
        'stems': status.get('stems', {}),
        'error': status.get('error')
    })


@app.route('/download/<job_id>/<stem>')
def download_stem(job_id, stem):
    """Download a separated stem"""
    if job_id not in processing_status:
        return jsonify({'success': False, 'error': 'Job not found'}), 404

    status = processing_status[job_id]
    if status['status'] != 'completed':
        return jsonify({'success': False, 'error': 'Job not completed'}), 400

    if stem not in status['stems']:
        return jsonify({'success': False, 'error': 'Stem not found'}), 404

    stem_path = Path(status['stems'][stem])
    if not stem_path.exists():
        return jsonify({'success': False, 'error': 'File not found'}), 404

    return send_file(stem_path, as_attachment=True)


@app.route('/upgrade', methods=['POST'])
def upgrade_tier():
    """Upgrade subscription tier (demo - no payment processing)"""
    user = get_user_session()
    data = request.get_json()

    new_tier = data.get('tier')
    if new_tier not in SUBSCRIPTION_TIERS:
        return jsonify({'success': False, 'error': 'Invalid tier'}), 400

    # In production, handle payment here
    user['tier'] = new_tier
    session['tier'] = new_tier

    return jsonify({
        'success': True,
        'tier': new_tier,
        'message': f'Successfully upgraded to {SUBSCRIPTION_TIERS[new_tier]["name"]}!'
    })


@app.route('/history')
def get_history():
    """Get user's processing history"""
    user = get_user_session()
    return jsonify({
        'success': True,
        'history': user.get('history', []),
        'total_processed': user['total_processed'],
        'monthly_usage': user['monthly_usage']
    })


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    model_ready = demucs_model is not None
    return jsonify({
        'status': 'healthy',
        'model_loaded': model_ready,
        'queue_size': processing_queue.qsize()
    })


if __name__ == '__main__':
    print("🎵 Car Wash Mixer - Web Application")
    print("=" * 50)
    print("Starting server...")
    print("Loading Demucs AI model in background...")
    print("\nOpen http://localhost:5000 in your browser")
    print("=" * 50)

    app.run(host='0.0.0.0', port=5000, debug=True)
