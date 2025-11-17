# Facial Recognition System for CCTV Video Analysis

A comprehensive facial recognition system built with FastAPI and Python for processing CCTV camera videos. This system can detect faces, recognize registered persons, and provide a web interface for management and monitoring.

## Features

- **Person Registration**: Register individuals with their face images
- **Video Processing**: Upload and process CCTV videos for face detection
- **Face Recognition**: Automatically identify registered persons in videos
- **Web Dashboard**: User-friendly interface for all operations
- **RESTful API**: Complete API for integration with other systems
- **Detection Monitoring**: View and filter detection history
- **Statistics Dashboard**: Real-time statistics and analytics

## System Architecture

```
facial-recognition-system/
├── app/                        # Application code
│   ├── api/                    # API routes
│   │   └── routes/             # Endpoint definitions
│   ├── core/                   # Core functionality
│   │   ├── face_detector.py    # Face detection logic
│   │   ├── face_recognizer.py  # Face recognition logic
│   │   └── video_processor.py  # Video processing pipeline
│   ├── models/                 # Database models
│   └── schemas/                # Pydantic schemas
├── frontend/                   # Web interface
│   ├── static/                 # CSS and JavaScript
│   └── templates/              # HTML templates
├── data/                       # Data storage
│   ├── database/               # SQLite database
│   ├── uploads/                # Uploaded videos
│   ├── known_faces/            # Registered face images
│   └── detections/             # Detection results
└── config.yaml                 # Configuration file
```

## Prerequisites

- macOS (tested on M4)
- Python 3.11+
- PyCharm (recommended) or any Python IDE

## Installation

### 1. Clone or Navigate to the Project

```bash
cd /Users/muhammaddattijo/Downloads/facial-recognition-system
```

### 2. Activate Virtual Environment

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note for MacBook M4 Users**: If you encounter issues with `face-recognition` or `dlib`, you may need to install additional dependencies:

```bash
# Install cmake and dlib dependencies
brew install cmake
brew install boost
brew install boost-python3

# Then retry pip install
pip install -r requirements.txt
```

### 4. Initialize Database

```bash
python -m app.models.database
```

## Configuration

Edit `config.yaml` to customize settings:

```yaml
# Face Recognition Settings
face_recognition:
  model: "hog"           # Use "hog" for CPU (faster) or "cnn" for GPU (more accurate)
  tolerance: 0.6         # Lower = stricter matching (0.0 - 1.0)
  num_jitters: 1         # Higher = more accurate but slower

# Video Processing
video:
  frame_skip: 5          # Process every Nth frame
  max_upload_size_mb: 500
  resize_width: 640      # Resize frames for faster processing
```

## Running the Application

### Start the Server

```bash
python -m app.main
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at: `http://localhost:8000`

## Usage Guide

### 1. Register Persons

1. Navigate to `http://localhost:8000/register`
2. Fill in the person's details
3. Upload a clear face image (only one face should be visible)
4. Click "Register Person"

### 2. Process CCTV Videos

1. Go to the Dashboard at `http://localhost:8000`
2. Upload a video file (MP4, AVI, MOV, MKV)
3. Configure processing options:
   - Frame skip: Process every Nth frame (higher = faster but may miss detections)
   - Save frames: Save images of detected faces
4. Click "Process Video"
5. View results showing detected persons and statistics

### 3. Monitor Detections

1. Navigate to `http://localhost:8000/monitor`
2. Use filters to search detections:
   - By person
   - By video
   - Unknown faces only
3. View detection timeline and statistics

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

#### Person Management

- `POST /api/v1/persons/` - Register a new person
- `GET /api/v1/persons/` - List all persons
- `GET /api/v1/persons/{id}` - Get person details
- `PUT /api/v1/persons/{id}` - Update person
- `DELETE /api/v1/persons/{id}` - Deactivate person

#### Video Processing

- `POST /api/v1/video/process` - Process a video file
- `GET /api/v1/video/uploads` - List uploaded videos
- `DELETE /api/v1/video/uploads/{filename}` - Delete video

#### Detections

- `GET /api/v1/detections/` - List detections with filters
- `GET /api/v1/detections/stats` - Get detection statistics
- `GET /api/v1/detections/{id}` - Get specific detection
- `GET /api/v1/detections/person/{id}/timeline` - Person timeline

## API Examples

### Register a Person (cURL)

```bash
curl -X POST "http://localhost:8000/api/v1/persons/" \
  -H "Content-Type: multipart/form-data" \
  -F "name=John Doe" \
  -F "employee_id=EMP001" \
  -F "email=john@example.com" \
  -F "department=Engineering" \
  -F "image=@/path/to/photo.jpg"
```

### Process a Video (Python)

```python
import requests

url = "http://localhost:8000/api/v1/video/process"

files = {'video': open('cctv_footage.mp4', 'rb')}
data = {
    'frame_skip': 5,
    'save_frames': True,
    'confidence_threshold': 0.6
}

response = requests.post(url, files=files, data=data)
result = response.json()

print(f"Total detections: {result['total_detections']}")
print(f"Known persons: {result['known_detections']}")
print(f"Unknown persons: {result['unknown_detections']}")
```

### Query Detections (Python)

```python
import requests

url = "http://localhost:8000/api/v1/detections/"
params = {
    'person_id': 1,
    'limit': 100
}

response = requests.get(url, params=params)
data = response.json()

for detection in data['detections']:
    print(f"{detection['person_name']} detected at {detection['timestamp']}")
```

## Performance Optimization

### For Faster Processing:
1. Increase `frame_skip` (e.g., 10 or 15) to process fewer frames
2. Use `model: "hog"` instead of "cnn"
3. Reduce `resize_width` in config
4. Set `save_frames: false` if you don't need detection images

### For Better Accuracy:
1. Use `model: "cnn"` (requires GPU)
2. Decrease `frame_skip` to 1-3
3. Increase `num_jitters` to 2-5
4. Lower `tolerance` to 0.5 or below

## Troubleshooting

### Issue: "No face detected in the image"
- Ensure the image has good lighting
- Face should be clearly visible and front-facing
- Image should contain only one face

### Issue: Video processing is slow
- Increase `frame_skip` value
- Use smaller video resolution
- Ensure `model` is set to "hog" for CPU processing

### Issue: Low recognition accuracy
- Adjust `tolerance` in config (lower = stricter)
- Use higher quality images for registration
- Ensure good lighting in CCTV footage

### Issue: Installation errors on M4 Mac
```bash
# Try these commands
brew install cmake boost boost-python3
export CMAKE_ARGS="-DCMAKE_OSX_ARCHITECTURES=arm64"
pip install --no-cache-dir dlib
pip install face-recognition
```

## Database Schema

### Persons Table
- `id`: Primary key
- `name`: Full name
- `email`: Email address
- `employee_id`: Unique employee identifier
- `face_encoding`: Serialized face encoding (128D vector)
- `image_path`: Path to registered face image
- `is_active`: Active status

### Detections Table
- `id`: Primary key
- `person_id`: Foreign key to persons
- `video_name`: Source video filename
- `frame_number`: Frame number in video
- `timestamp`: Detection timestamp
- `confidence`: Recognition confidence (0.0-1.0)
- `face_location`: Bounding box coordinates
- `is_unknown`: Whether person is unknown

## Development

### Running Tests

```bash
pytest tests/
```

### Code Structure

- **Core Modules** (`app/core/`): Contain the facial recognition logic
- **API Routes** (`app/api/routes/`): RESTful API endpoints
- **Models** (`app/models/`): Database schema definitions
- **Schemas** (`app/schemas/`): Request/response validation

## Security Considerations

1. **Change default SECRET_KEY** in `.env` file for production
2. **Restrict CORS origins** in production environment
3. **Use HTTPS** for production deployment
4. **Implement authentication** for API endpoints
5. **Validate file uploads** to prevent malicious files
6. **Regular backups** of the database and registered faces

## Future Enhancements

- [ ] Real-time CCTV camera stream processing
- [ ] Email/SMS alerts for specific person detections
- [ ] Multi-camera support
- [ ] Advanced analytics and reporting
- [ ] Docker containerization
- [ ] PostgreSQL support for production
- [ ] User authentication and role-based access
- [ ] Export detection reports (PDF, CSV)

## License

This project is for educational and authorized use only.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation at `/docs`
3. Check configuration in `config.yaml`

## Acknowledgments

Built with:
- FastAPI - Web framework
- face_recognition - Face detection and recognition
- OpenCV - Video processing
- SQLAlchemy - Database ORM
- Bootstrap concepts - UI design

---

**Version**: 1.0.0
**Last Updated**: 2025-11-08
