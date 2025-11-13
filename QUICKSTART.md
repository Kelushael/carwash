# Quick Start Guide - Car Wash Mixer Web App

## Installation

```bash
# Clone the repository
git clone https://github.com/Kelushael/carwash.git
cd carwash

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Web Application

```bash
python3 app.py
```

Open your browser to: **http://localhost:5000**

The Demucs AI model (~300MB) will download automatically on first use.

## Usage Flow

1. **Upload Your Track**
   - Click "Select File" or drag & drop your audio file
   - Supported formats: MP3, WAV, FLAC, M4A, OGG, AAC
   - Max file size: 200MB

2. **Processing**
   - Click "Start Separation"
   - AI will process your track (2-5 minutes depending on length)
   - Status updates in real-time

3. **Download Stems**
   - Once complete, download individual stems
   - Each stem is a separate WAV file
   - High-quality, studio-ready audio

## Subscription Tiers

### Free Tier (Default)
- 2 songs per month
- 2-stem separation (vocals + instrumental)
- Perfect for trying out the service

### Pro Tier ($9.99/month)
- 20 songs per month
- Full 4-stem separation (vocals, drums, bass, other)
- Priority processing queue
- Higher quality exports

### Premium Tier ($29.99/month)
- Unlimited songs
- Full 4-stem separation
- Fastest processing
- Batch upload support
- API access for automation

## Upgrade Your Tier

On the main page, scroll to "Choose Your Plan" and click "Upgrade" on your desired tier.

**Note**: This is a demo implementation. In production, this would integrate with a payment processor like Stripe.

## Technical Requirements

- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended)
- ~2GB disk space for model and processing
- FFmpeg installed (for audio processing)

### Install FFmpeg

**macOS**:
```bash
brew install ffmpeg
```

**Ubuntu/Debian**:
```bash
sudo apt install ffmpeg
```

**Windows**:
Download from https://ffmpeg.org/download.html

## Troubleshooting

### Model Won't Load
- Check internet connection (needed for first download)
- Ensure you have ~500MB free disk space
- Check Python version: `python3 --version` (need 3.8+)

### Processing Stuck
- Check logs in terminal
- Ensure file is valid audio format
- Try a smaller file first (under 10MB)

### Upload Fails
- Check file size (max 200MB)
- Verify file format is supported
- Check available disk space

## Development Mode

To run in development mode with auto-reload:

```bash
export FLASK_ENV=development
python3 app.py
```

## Production Deployment

For production use, consider:

1. **Use a production WSGI server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Add a reverse proxy** (nginx)

3. **Use a real database** (PostgreSQL, MySQL)

4. **Add authentication** (OAuth, JWT)

5. **Implement payment processing** (Stripe, PayPal)

6. **Use cloud storage** for files (S3, GCS)

7. **Add rate limiting** and security headers

## API Usage (Premium Tier)

### Upload File
```bash
curl -X POST http://localhost:5000/upload \
  -F "file=@song.mp3" \
  -H "Cookie: session=YOUR_SESSION_ID"
```

### Check Status
```bash
curl http://localhost:5000/status/JOB_ID
```

### Download Stem
```bash
curl -O http://localhost:5000/download/JOB_ID/vocals
```

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check the main README.md for more details

---

**Enjoy separating stems!** 🎵
