# ✨ Enhanced System - Cross-Video Face Tracking

## 🎯 What You Asked For

> "I want it to not just compare registered faces, but also compare faces detected from video A to video B. Save those faces and compare them against previous faces found in other videos."

## ✅ What You Got

Your system now has **TWO MODES**:

### Mode 1: Basic System (Original)
```bash
python start_server.py
```
- Compares faces to registered persons only
- Unknown faces are ignored

### Mode 2: Enhanced System (NEW!) ⭐
```bash
python start_enhanced.py
```
- Compares faces to registered persons
- **Compares faces to unknowns from previous videos**
- **Automatically saves and tracks unknown persons**
- **Links same person across multiple videos**

---

## 🧠 How It Works - Simple Explanation

### Example: 3 Videos Over 3 Days

**Monday - Video 1:**
```
Process: office_monday.mp4

Found faces:
├─ John (registered) → "This is John" ✅
├─ Face #2 (not registered) → Save as "Unknown-0001" 💾
└─ Face #3 (not registered) → Save as "Unknown-0002" 💾

Database now has:
- Registered: John
- Unknown: Unknown-0001, Unknown-0002
```

**Tuesday - Video 2:**
```
Process: office_tuesday.mp4

System checks each face against:
1. Registered persons: John
2. Unknown persons: Unknown-0001, Unknown-0002

Found faces:
├─ John → "This is John" ✅
├─ Face matches Unknown-0001 → "Unknown-0001 (2nd sighting)" ✅
├─ Face matches Unknown-0002 → "Unknown-0002 (2nd sighting)" ✅
└─ New face → Save as "Unknown-0003" 💾

Database updated:
- Unknown-0001: seen 2 times
- Unknown-0002: seen 2 times
- Unknown-0003: seen 1 time (new)
```

**Wednesday - Video 3:**
```
Process: office_wednesday.mp4

Found faces:
├─ John → "This is John" ✅
├─ Unknown-0001 → "Unknown-0001 (3rd sighting)" ✅
└─ Unknown-0002 → "Unknown-0002 (3rd sighting)" ✅

You identify Unknown-0001: "Oh! That's Mike from HR!"

Promote Unknown-0001 → Mike
Result: All 3 past sightings now linked to "Mike"
```

---

## 📊 New Database Tables

### unknown_persons (NEW!)
Stores faces detected in videos that aren't registered

| Column | Description |
|--------|-------------|
| `identifier` | Auto-generated ID like "Unknown-0001" |
| `face_encoding` | Face data (for matching) |
| `total_detections` | How many times seen |
| `first_seen` | First detection timestamp |
| `last_seen` | Latest detection timestamp |
| `representative_image_path` | Sample image of this person |

### detections (Updated)
Now links to EITHER a registered person OR an unknown person

| Column | What It Means |
|--------|---------------|
| `person_id` | Links to registered person (if known) |
| `unknown_person_id` | Links to unknown person (if tracked) |
| `detection_type` | "registered", "unknown_tracked", or "unknown_new" |

---

## 🚀 Quick Start Guide

### Step 1: Initialize Enhanced Database
```bash
python -m app.models.enhanced_database
```

### Step 2: Start Enhanced Server
```bash
python start_enhanced.py
```

### Step 3: Process First Video
```bash
curl -X POST "http://localhost:8000/api/v1/enhanced-video/process" \
  -F "video=@video1.mp4"
```

**Output:**
```json
{
  "breakdown": {
    "registered_persons": 5,
    "tracked_unknowns": 0,        ← No previous unknowns yet
    "new_unknowns": 3             ← 3 new unknown persons saved
  },
  "new_unknowns_created": 3
}
```

### Step 4: Process Second Video
```bash
curl -X POST "http://localhost:8000/api/v1/enhanced-video/process" \
  -F "video=@video2.mp4"
```

**Output:**
```json
{
  "breakdown": {
    "registered_persons": 8,
    "tracked_unknowns": 12,       ← Matched from video 1! ✅
    "new_unknowns": 2             ← 2 brand new unknowns
  }
}
```

### Step 5: View All Unknown Persons
```bash
curl "http://localhost:8000/api/v1/enhanced-video/unknown-persons"
```

**Output:**
```json
{
  "unknown_persons": [
    {
      "identifier": "Unknown-0001",
      "total_detections": 15,
      "first_seen": "2025-11-08 09:00:00",
      "last_seen": "2025-11-10 17:00:00"
    },
    {
      "identifier": "Unknown-0002",
      "total_detections": 8,
      ...
    }
  ]
}
```

### Step 6: Check Where Unknown Appeared
```bash
curl "http://localhost:8000/api/v1/enhanced-video/unknown-persons/1/timeline"
```

**Output:**
```json
{
  "identifier": "Unknown-0001",
  "total_detections": 15,
  "videos_appeared_in": 3,
  "timeline": [
    {"video": "video1.mp4", "timestamp": "..."},
    {"video": "video2.mp4", "timestamp": "..."},
    {"video": "video3.mp4", "timestamp": "..."}
  ]
}
```

### Step 7: Promote to Registered Person
```bash
curl -X POST "http://localhost:8000/api/v1/enhanced-video/unknown-persons/1/promote" \
  -F "name=Mike Johnson" \
  -F "email=mike@company.com"
```

**Output:**
```json
{
  "message": "Successfully promoted Unknown-0001 to registered person",
  "person_name": "Mike Johnson",
  "detections_transferred": 15   ← All 15 past sightings now linked!
}
```

---

## 🎮 Using Python

```python
import requests

# Process a video
response = requests.post(
    "http://localhost:8000/api/v1/enhanced-video/process",
    files={"video": open("cctv.mp4", "rb")},
    data={"save_frames": True}
)

result = response.json()
print(f"Registered: {result['breakdown']['registered_persons']}")
print(f"Tracked unknowns: {result['breakdown']['tracked_unknowns']}")
print(f"New unknowns: {result['breakdown']['new_unknowns']}")

# List unknown persons
response = requests.get(
    "http://localhost:8000/api/v1/enhanced-video/unknown-persons",
    params={"min_detections": 5}  # Only those seen 5+ times
)

for unknown in response.json()["unknown_persons"]:
    print(f"{unknown['identifier']}: {unknown['total_detections']} sightings")
```

---

## 🔄 Workflow Diagram

```
┌──────────────┐
│  Video 1     │
│  (Monday)    │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────┐
│ Process with Enhanced System    │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Results:                        │
│ - John (registered) ✓           │
│ - Unknown-0001 (new) 💾         │
│ - Unknown-0002 (new) 💾         │
└─────────────────────────────────┘
       │
       │ DATABASE NOW HAS:
       │ Unknowns: 0001, 0002
       │
       ▼
┌──────────────┐
│  Video 2     │
│  (Tuesday)   │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────┐
│ Check against:                  │
│ 1. Registered (John)            │
│ 2. Unknowns (0001, 0002)        │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Results:                        │
│ - John ✓                        │
│ - Unknown-0001 ✓ (matched!)     │
│ - Unknown-0002 ✓ (matched!)     │
│ - Unknown-0003 (new) 💾         │
└─────────────────────────────────┘
       │
       │ UPDATED DATABASE:
       │ 0001: 2 sightings
       │ 0002: 2 sightings
       │ 0003: 1 sighting
       │
       ▼
┌──────────────┐
│ Identify     │
│ Unknown-0001 │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────┐
│ Promote to "Mike"               │
│ → All past sightings linked     │
└─────────────────────────────────┘
```

---

## 📁 File Structure

```
Enhanced System Files:
├── app/
│   ├── models/
│   │   └── enhanced_database.py          ⭐ NEW tables
│   ├── core/
│   │   ├── enhanced_recognizer.py        ⭐ Cross-video matching
│   │   └── enhanced_video_processor.py   ⭐ Tracking processor
│   ├── api/routes/
│   │   └── enhanced_video.py             ⭐ NEW endpoints
│   └── main_enhanced.py                  ⭐ Enhanced app
│
├── start_enhanced.py                     ⭐ Start script
├── CROSS_VIDEO_TRACKING.md              ⭐ Complete guide
└── ENHANCED_FEATURES.md                 ⭐ This file
```

---

## 🎯 Use Cases

### Security Monitoring
- Track suspicious persons across multiple days
- Build database of regular visitors automatically
- Alert when unknown person appears repeatedly

### Investigation
- Find all videos where Unknown-0005 appeared
- Check timeline: when did they first appear?
- Cross-reference with incident reports

### Visitor Management
- Unknown person appears 5 times → likely a contractor
- Review and promote to registered person
- Future visits automatically recognized

---

## ⚙️ Configuration

**Matching Thresholds:**

```python
# Stricter for registered persons
registered_tolerance = 0.85  # 85% similarity required

# Slightly looser for unknown matching
unknown_tolerance = 0.80     # 80% similarity required
```

**Why two thresholds?**
- Registered persons: Have clear, well-lit registration photos → stricter
- Unknown persons: Detected from video (variable quality) → slightly looser

---

## 📊 API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/enhanced-video/process` | Process video with tracking |
| `GET /api/v1/enhanced-video/unknown-persons` | List all unknown persons |
| `GET /api/v1/enhanced-video/unknown-persons/{id}/timeline` | See where person appeared |
| `POST /api/v1/enhanced-video/unknown-persons/{id}/promote` | Convert to registered person |

---

## 🎓 Comparison

### Basic vs Enhanced

| Feature | Basic | Enhanced |
|---------|-------|----------|
| Match registered persons | ✅ | ✅ |
| Track unknown persons | ❌ | ✅ |
| Cross-video matching | ❌ | ✅ |
| Unknown person timeline | ❌ | ✅ |
| Promote unknown→registered | ❌ | ✅ |
| Automatic database building | ❌ | ✅ |

---

## 💡 Pro Tips

### Tip 1: Process in Chronological Order
```bash
# Process oldest to newest for better tracking
python process_video.py monday.mp4
python process_video.py tuesday.mp4
python process_video.py wednesday.mp4
```

### Tip 2: Review Frequent Unknowns Weekly
```bash
# Get unknowns seen 10+ times
curl "http://localhost:8000/api/v1/enhanced-video/unknown-persons?min_detections=10"

# Review and promote identified persons
```

### Tip 3: Use for Investigations
```python
# Find all videos with Unknown-0007
timeline = get_unknown_timeline(7)

# Check if they appeared during incident timeframe
suspicious = [t for t in timeline
              if incident_start < t["timestamp"] < incident_end]
```

---

## 🚀 Get Started Now

```bash
# 1. Initialize
python -m app.models.enhanced_database

# 2. Start
python start_enhanced.py

# 3. Use
# Upload videos via API or web interface

# 4. Review
curl "http://localhost:8000/api/v1/enhanced-video/unknown-persons"
```

---

## 🎉 Summary

**You asked for:**
- ✅ Compare faces across videos
- ✅ Save unknown faces
- ✅ Match against previous unknowns

**You got:**
- ✅ All of the above
- ✅ Unknown person tracking database
- ✅ Timeline for each unknown person
- ✅ Ability to promote unknowns to registered
- ✅ Complete audit trail

**This is exactly what you requested!** 🎯

---

Read **CROSS_VIDEO_TRACKING.md** for detailed examples and workflows!
