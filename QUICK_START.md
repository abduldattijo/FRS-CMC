# Quick Start Guide

Get your Facial Recognition System up and running in 5 minutes!

## Step 1: Install Dependencies

```bash
# Make sure your virtual environment is activated
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

**For M4 Mac users**, if you encounter issues with `dlib` or `face-recognition`:

```bash
brew install cmake boost boost-python3
pip install --no-cache-dir dlib
pip install face-recognition
```

## Step 2: Verify Installation

Run the system test to verify everything is installed correctly:

```bash
python tests/test_system.py
```

You should see all tests pass with green checkmarks (✓).

## Step 3: Initialize Database

The database will be automatically initialized when you run the tests. If you want to manually initialize it:

```bash
python -m app.models.database
```

## Step 4: Start the Server

```bash
python run.py
```

The server will start on `http://localhost:8000`

## Step 5: Access the Web Interface

Open your browser and navigate to:

- **Dashboard**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Your First Recognition Task

### 1. Register a Person

1. Go to http://localhost:8000/register
2. Fill in the form:
   - Name: John Doe
   - Employee ID: EMP001
   - Upload a clear face photo
3. Click "Register Person"

### 2. Process a Video

1. Go to http://localhost:8000 (Dashboard)
2. Click "Select Video File" or drag and drop a video
3. Configure settings (default settings work fine)
4. Click "Process Video"
5. Wait for processing to complete
6. View the results!

### 3. Monitor Detections

1. Go to http://localhost:8000/monitor
2. View all detections with filters
3. See statistics and timelines

## Testing with Sample Video

If you don't have a CCTV video yet, you can:

1. Use your phone to record a short video (10-30 seconds)
2. Make sure your face is clearly visible
3. First register yourself using a photo
4. Then upload and process the video
5. The system should detect and recognize you!

## Common Commands

```bash
# Start server
python run.py

# Start with auto-reload (development)
uvicorn app.main:app --reload

# Run tests
python tests/test_system.py

# Check database
python -m app.models.database
```

## Performance Tips

For faster processing during testing:
- Set `frame_skip: 10` in the video upload form
- Use shorter videos (< 1 minute)
- Use `model: "hog"` in config.yaml

## Troubleshooting

### Server won't start
- Check if port 8000 is already in use
- Verify all dependencies are installed
- Check the .env file exists

### Video processing is slow
- Increase frame_skip value
- Use smaller video files
- Check CPU usage

### Face not detected
- Ensure good lighting in the photo
- Face should be front-facing
- Only one face per registration photo

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the API at http://localhost:8000/docs
- Customize settings in `config.yaml`
- Add more persons and process more videos!

## Need Help?

Check these resources:
1. Full documentation in README.md
2. API documentation at /docs
3. Troubleshooting section in README.md
4. Configuration guide in config.yaml

---

Happy recognizing! 🎥👤
