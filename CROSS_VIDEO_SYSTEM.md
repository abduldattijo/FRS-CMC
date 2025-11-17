# Cross-Video Identity Linking System

## Overview

An intelligence platform for tracking individuals across multiple CCTV videos. This system identifies the same person appearing in different videos without comparing faces within the same video.

**Perfect for:** Intelligence agencies, surveillance operations, security analysis, investigative work.

---

## 🎯 What This System Does

### The Problem It Solves

You have multiple CCTV videos (A, B, C, D, E...) and need to:
- Identify unique individuals in each video
- Find if the same person appears across different videos
- Build a network showing: "Person X appears in videos A, C, and E"
- **Never** waste time comparing faces within the same video

### The Solution

**Cross-video identity linking** - Compare faces ONLY across different videos:
```
Video A faces ↔ Video B faces ✓
Video A faces ↔ Video C faces ✓
Video B faces ↔ Video C faces ✓

Video A faces ↔ Video A faces ✗ (NEVER)
Video B faces ↔ Video B faces ✗ (NEVER)
```

---

## 📊 System Architecture

### Processing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ 1. VIDEO UPLOAD & PROCESSING                                │
├─────────────────────────────────────────────────────────────┤
│ Upload Video A → Extract Frames → Detect Faces              │
│                                                              │
│ Raw Detections (e.g., 500 faces from 100 frames)            │
│         ↓                                                    │
│ CLUSTERING (De-duplicate within video)                      │
│         ↓                                                    │
│ Unique Faces (e.g., 5 unique people)                        │
│         ↓                                                    │
│ Save to Database as VideoFaces                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 2. CROSS-VIDEO ANALYSIS                                     │
├─────────────────────────────────────────────────────────────┤
│ Compare:                                                     │
│   Video A Faces (5) ↔ Video B Faces (7) = 35 comparisons   │
│   Video A Faces (5) ↔ Video C Faces (3) = 15 comparisons   │
│   Video B Faces (7) ↔ Video C Faces (3) = 21 comparisons   │
│                                                              │
│ Total: 71 comparisons (NOT 500 × 500 × 500!)               │
│         ↓                                                    │
│ Find Matches (similarity > threshold)                       │
│         ↓                                                    │
│ Build PersonClusters                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 3. RESULTS                                                   │
├─────────────────────────────────────────────────────────────┤
│ PERSON_0001: Appears in Videos A, C (12 total appearances) │
│ PERSON_0002: Appears in Videos B, D (8 total appearances)  │
│ PERSON_0003: Appears in Videos A, B, E (15 appearances)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Schema

### Tables

1. **videos** - Tracks uploaded CCTV videos
   - Metadata: filename, duration, fps, resolution
   - Processing status: pending, processing, completed, failed
   - Statistics: total faces detected, unique faces count

2. **video_faces** - Unique faces per video (de-duplicated)
   - One entry per unique person per video
   - Face encoding (128D or 478D vector)
   - Appearance statistics within the video
   - Representative image (best quality)

3. **raw_detections** - All individual face detections
   - Links to parent VideoFace
   - Frame number, timestamp, bounding box
   - Individual face encoding
   - Detection image path

4. **person_clusters** - People tracked across videos
   - Auto-generated ID (e.g., "PERSON_0001")
   - Total videos appeared in
   - Total appearances across all videos
   - Representative encoding (mean of all)
   - Optional manual identification

5. **cross_video_matches** - Face similarity matches
   - Source face ↔ Target face
   - Similarity score (0.0-1.0)
   - Only stores matches between DIFFERENT videos
   - Manual confirmation status

6. **analysis_jobs** - Tracks analysis runs
   - Job metadata and parameters
   - Processing statistics
   - Results summary

---

## 🚀 Installation

### Prerequisites

- Python 3.11+
- macOS (M4 optimized) or Linux
- Virtual environment activated

### Setup

```bash
cd /Users/muhammaddattijo/Downloads/facial-recognition-system

# Activate virtual environment
source .venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Initialize the cross-video database
python -m app.models.cross_video_database
```

**Expected Output:**
```
============================================================
Cross-Video Identity Linking Database Initialized!
============================================================

Tables created:
  ✓ videos - Track uploaded CCTV videos
  ✓ video_faces - Unique faces per video (de-duplicated)
  ✓ raw_detections - All individual face detections
  ✓ person_clusters - People tracked across videos
  ✓ cross_video_matches - Face similarity matches between videos
  ✓ analysis_jobs - Track analysis tasks
```

---

## 🎮 Usage

### Start the Server

```bash
python start_cross_video.py
```

**Access:**
- Dashboard: http://localhost:8001
- API Docs: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

### Workflow

#### Step 1: Upload Videos

Upload multiple CCTV videos through the web interface or API.

**Web Interface:**
1. Go to http://localhost:8001
2. Click "Upload Video"
3. Select video file
4. Set frame skip (default: 5)
5. Click "Upload & Process Video"

**API (cURL):**
```bash
curl -X POST "http://localhost:8001/api/v1/cross-video/upload-video" \
  -F "video=@video_A.mp4" \
  -F "frame_skip=5" \
  -F "save_frames=true"
```

**API (Python):**
```python
import requests

url = "http://localhost:8001/api/v1/cross-video/upload-video"

with open("video_A.mp4", "rb") as f:
    files = {"video": f}
    data = {"frame_skip": 5, "save_frames": True}
    response = requests.post(url, files=files, data=data)

print(response.json())
```

#### Step 2: Process Multiple Videos

Repeat Step 1 for each video (B, C, D, E...).

The system will:
- Extract frames from each video
- Detect faces in frames
- Cluster faces to identify unique individuals within each video
- Save VideoFace entries to database

#### Step 3: Run Cross-Video Analysis

Once all videos are processed, run the analysis:

**Web Interface:**
1. Click "Run Full Analysis" button
2. Wait for completion
3. View results

**API:**
```bash
curl -X POST "http://localhost:8001/api/v1/cross-video/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "similarity_threshold": 0.85,
    "clustering_threshold": 0.90
  }'
```

**Python:**
```python
import requests

url = "http://localhost:8001/api/v1/cross-video/analyze"

response = requests.post(url, json={
    "similarity_threshold": 0.85,
    "clustering_threshold": 0.90
})

result = response.json()
print(f"Total comparisons: {result['analysis_results']['total_comparisons']}")
print(f"Matches found: {result['analysis_results']['total_matches_found']}")
print(f"Person clusters: {result['analysis_results']['total_person_clusters']}")
```

#### Step 4: View Results

**List Person Clusters:**
```bash
curl "http://localhost:8001/api/v1/cross-video/clusters"
```

**Get Cluster Details:**
```bash
curl "http://localhost:8001/api/v1/cross-video/clusters/1"
```

**Example Response:**
```json
{
  "cluster_id": 1,
  "cluster_identifier": "PERSON_0001",
  "total_videos": 3,
  "total_appearances": 45,
  "first_seen": "2025-11-09T10:30:00",
  "last_seen": "2025-11-09T14:45:00",
  "video_appearances": [
    {
      "video_id": 1,
      "video_filename": "cctv_A.mp4",
      "appearances": 15,
      "first_seen": "2025-11-09T10:30:00",
      "last_seen": "2025-11-09T11:00:00"
    },
    {
      "video_id": 3,
      "video_filename": "cctv_C.mp4",
      "appearances": 20,
      "first_seen": "2025-11-09T13:00:00",
      "last_seen": "2025-11-09T14:00:00"
    },
    {
      "video_id": 5,
      "video_filename": "cctv_E.mp4",
      "appearances": 10,
      "first_seen": "2025-11-09T14:15:00",
      "last_seen": "2025-11-09T14:45:00"
    }
  ]
}
```

**Identify a Person:**
```bash
curl -X POST "http://localhost:8001/api/v1/cross-video/clusters/1/identify" \
  -F "name=John Doe" \
  -F "notes=Suspect in investigation #12345"
```

---

## 🔬 API Reference

### Video Endpoints

- `POST /api/v1/cross-video/upload-video` - Upload and process video
- `GET /api/v1/cross-video/videos` - List all videos
- `GET /api/v1/cross-video/videos/{id}` - Get video details
- `DELETE /api/v1/cross-video/videos/{id}` - Delete video

### Analysis Endpoints

- `POST /api/v1/cross-video/analyze` - Run cross-video analysis
- `GET /api/v1/cross-video/jobs` - List analysis jobs

### Cluster Endpoints

- `GET /api/v1/cross-video/clusters` - List person clusters
- `GET /api/v1/cross-video/clusters/{id}` - Get cluster details
- `POST /api/v1/cross-video/clusters/{id}/identify` - Identify person

### Match Endpoints

- `GET /api/v1/cross-video/matches` - Get cross-video matches

---

## ⚙️ Configuration

### Thresholds

**Similarity Threshold (0.85):**
- Minimum similarity to record a match between two faces
- Higher = stricter matching (fewer false positives)
- Lower = more matches (higher recall, more false positives)

**Clustering Threshold (0.90):**
- Minimum similarity to group faces into same PersonCluster
- Should be higher than similarity threshold
- Higher = more separate clusters (conservative)
- Lower = fewer, larger clusters (aggressive)

**Recommended Settings:**

| Use Case | Similarity | Clustering |
|----------|-----------|------------|
| High security (avoid false matches) | 0.90 | 0.95 |
| Balanced (default) | 0.85 | 0.90 |
| Maximize recall (catch all matches) | 0.75 | 0.80 |

---

## 📈 Performance

### Processing Speed

**Video Processing (per video):**
- Frame skip 5: ~2-5 seconds per minute of video
- Frame skip 10: ~1-3 seconds per minute of video

**Cross-Video Analysis:**
- 5 videos, 5 unique faces each: ~125 comparisons (~0.1s)
- 10 videos, 10 unique faces each: ~4,500 comparisons (~1s)
- 20 videos, 20 unique faces each: ~38,000 comparisons (~5-10s)

**Key Point:** System compares UNIQUE faces, not raw detections!
- 5 videos × 500 raw detections = 2,500 total
- After clustering: 5 videos × 5 unique = 25 faces
- Comparisons: 25 × 24 / 2 = 300 (not 2,500 × 2,499 / 2!)

---

## 🛠️ Advanced Usage

### Analyze Specific Videos Only

```python
# Only analyze videos 1, 3, and 5
response = requests.post(
    "http://localhost:8001/api/v1/cross-video/analyze",
    json={
        "video_ids": [1, 3, 5],
        "similarity_threshold": 0.85,
        "clustering_threshold": 0.90
    }
)
```

### Filter Clusters by Appearance

```bash
# Only show persons appearing in 3+ videos
curl "http://localhost:8001/api/v1/cross-video/clusters?min_videos=3"
```

### Get High-Confidence Matches

```bash
# Only matches with 90%+ similarity
curl "http://localhost:8001/api/v1/cross-video/matches?min_similarity=0.90&limit=50"
```

---

## 📁 File Structure

```
facial-recognition-system/
├── app/
│   ├── models/
│   │   └── cross_video_database.py    # Database schema
│   ├── core/
│   │   ├── face_clustering.py          # Within-video de-duplication
│   │   ├── cross_video_matcher.py      # Cross-video matching
│   │   └── cross_video_processor.py    # Video processing
│   ├── api/routes/
│   │   └── cross_video.py              # API endpoints
│   └── main_cross_video.py             # FastAPI app
├── frontend/templates/
│   └── cross_video_dashboard.html      # Web UI
├── data/
│   ├── cross_video.db                  # SQLite database
│   ├── cross_video_uploads/            # Uploaded videos
│   └── cross_video_detections/         # Detection images
├── start_cross_video.py                # Startup script
└── CROSS_VIDEO_SYSTEM.md               # This file
```

---

## 🔍 Example Workflow

### Intelligence Investigation Example

**Scenario:** You have 5 CCTV videos from different locations and times. You need to identify if any individuals appear in multiple locations.

**Step 1: Upload Videos**
```bash
# Upload all 5 videos
for video in mall_entrance.mp4 bank_atm.mp4 parking_lot.mp4 subway_station.mp4 airport_terminal.mp4; do
    curl -X POST "http://localhost:8001/api/v1/cross-video/upload-video" \
      -F "video=@$video" \
      -F "frame_skip=5"
done
```

**Step 2: Run Analysis**
```bash
curl -X POST "http://localhost:8001/api/v1/cross-video/analyze" \
  -H "Content-Type: application/json" \
  -d '{"similarity_threshold": 0.88, "clustering_threshold": 0.92}'
```

**Step 3: Find Persons in Multiple Locations**
```bash
# Get persons appearing in 2+ videos
curl "http://localhost:8001/api/v1/cross-video/clusters?min_videos=2"
```

**Result:**
```json
{
  "total_clusters": 3,
  "clusters": [
    {
      "identifier": "PERSON_0001",
      "total_videos": 4,
      "total_appearances": 67,
      "videos": ["mall_entrance.mp4", "bank_atm.mp4", "subway_station.mp4", "airport_terminal.mp4"]
    },
    {
      "identifier": "PERSON_0002",
      "total_videos": 2,
      "total_appearances": 23,
      "videos": ["parking_lot.mp4", "subway_station.mp4"]
    }
  ]
}
```

**Analysis:**
- PERSON_0001 appears in 4 different locations (suspicious pattern!)
- PERSON_0002 appears in 2 locations

**Step 4: Identify Suspects**
```bash
curl -X POST "http://localhost:8001/api/v1/cross-video/clusters/1/identify" \
  -F "name=Suspect Alpha" \
  -F "notes=Person of interest - appeared at 4 different locations"
```

---

## 🧪 Testing

### Quick Test

```bash
# 1. Start server
python start_cross_video.py

# 2. In another terminal, run test
python -c "
import requests
import json

# Check health
health = requests.get('http://localhost:8001/health').json()
print('Health:', health)

# Get videos
videos = requests.get('http://localhost:8001/api/v1/cross-video/videos').json()
print(f'Total videos: {videos[\"total\"]}')

# Get clusters
clusters = requests.get('http://localhost:8001/api/v1/cross-video/clusters').json()
print(f'Total clusters: {clusters[\"total_clusters\"]}')
"
```

---

## 🎯 Key Differences from Original System

| Feature | Original System | Cross-Video System |
|---------|----------------|-------------------|
| **Purpose** | Recognize pre-registered persons | Track unknowns across videos |
| **Input** | Single images for registration | Multiple CCTV videos |
| **Comparison** | Video faces vs database | Video A faces vs Video B faces |
| **Output** | "Person detected in video" | "Person X in videos A, C, E" |
| **Use Case** | Access control, attendance | Investigation, surveillance |
| **Database** | Persons, Detections | Videos, VideoFaces, PersonClusters |

---

## 📝 Notes

### Optimization Tips

1. **Frame Skip:** Increase to 10-15 for faster processing (may miss brief appearances)
2. **Thresholds:** Adjust based on your accuracy requirements
3. **Video Quality:** Higher quality videos = better face detection
4. **Face Size:** Faces should be at least 50x50 pixels for reliable recognition

### Limitations

1. **Video Quality:** Poor lighting or low resolution reduces accuracy
2. **Face Angles:** Profile views are harder to match than frontal faces
3. **Occlusions:** Masks, glasses, hats can affect recognition
4. **Time Gaps:** Significant appearance changes (haircut, beard) may not match

### Future Enhancements

- [ ] Real-time video stream processing
- [ ] Network graph visualization of person movements
- [ ] Timeline reconstruction showing person's path across videos
- [ ] Integration with external databases for automatic identification
- [ ] Multi-person tracking in same frame
- [ ] Export investigation reports (PDF, JSON)

---

## 🔐 Security Considerations

1. **Data Privacy:** This system processes biometric data - ensure compliance with local laws
2. **Access Control:** Implement authentication for production use
3. **Audit Logging:** Track who accesses which person clusters
4. **Data Retention:** Define policies for how long to retain video and face data
5. **Secure Storage:** Encrypt sensitive data at rest

---

## 📞 Support

For issues or questions:
1. Check this documentation
2. Review API documentation at `/docs`
3. Check system logs
4. Review database schema

---

**Version:** 1.0.0
**Last Updated:** 2025-11-09
**Optimized For:** macOS M4, Python 3.11+
