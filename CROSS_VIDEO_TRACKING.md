

# 🎯 Cross-Video Face Tracking - Complete Guide

## 🚀 What Is This?

Your system now tracks faces **across multiple videos**!

### Before (Basic System):
```
Video A → Detect faces → Compare to registered persons
         └─> Unknown faces are ignored ❌

Video B → Detect faces → Compare to registered persons
         └─> Unknown faces are ignored ❌
```

### After (Enhanced System):
```
Video A → Detect faces → Compare to registered persons
         └─> Unknown faces → SAVED to database ✅

Video B → Detect faces → Compare to:
         ├─> Registered persons
         └─> Unknown faces from Video A ✅
              └─> If match → Link them together!
```

## 🧠 How It Works

### Phase 1: First Video (Monday)
```
Upload video: office_monday.mp4

Detections:
├─ John (registered) → Recognized ✅
├─ Jane (registered) → Recognized ✅
└─ Unknown face → SAVED as "Unknown-0001" 💾
```

### Phase 2: Second Video (Tuesday)
```
Upload video: office_tuesday.mp4

System checks each face against:
1. Registered persons (John, Jane)
2. Unknown persons (Unknown-0001 from Monday)

Detections:
├─ John → Recognized ✅
├─ Same unknown person → Matched to "Unknown-0001" ✅
│   └─> Update: "Unknown-0001" seen 2 times
└─> New unknown → SAVED as "Unknown-0002" 💾
```

### Phase 3: Third Video (Wednesday)
```
Upload video: office_wednesday.mp4

System checks against:
1. Registered: John, Jane
2. Unknown: Unknown-0001 (2 sightings), Unknown-0002 (1 sighting)

Detections:
├─ Unknown-0001 → Matched again! (3rd sighting)
└─> You realize: "Unknown-0001 is Mike from HR!"
    └─> Promote to registered person ✅
        └─> All past detections now linked to "Mike"
```

---

## 📊 Database Structure

### Three Tables:

**1. persons** (Registered People)
```sql
id | name | face_encoding | created_at
---|------|---------------|------------
1  | John | [binary data] | 2025-11-08
2  | Jane | [binary data] | 2025-11-08
```

**2. unknown_persons** (Tracked Unknowns) ⭐ NEW
```sql
id | identifier    | face_encoding | total_detections | first_seen | last_seen
---|---------------|---------------|------------------|------------|----------
1  | Unknown-0001  | [binary data] | 15               | 2025-11-08 | 2025-11-10
2  | Unknown-0002  | [binary data] | 3                | 2025-11-09 | 2025-11-09
```

**3. detections** (All Face Sightings)
```sql
id | person_id | unknown_person_id | video_name      | timestamp  | detection_type
---|-----------|-------------------|-----------------|------------|---------------
1  | 1         | NULL              | monday.mp4      | 09:15:00   | registered
2  | NULL      | 1                 | monday.mp4      | 09:16:00   | unknown_tracked
3  | NULL      | 1                 | tuesday.mp4     | 09:20:00   | unknown_tracked
4  | NULL      | 2                 | tuesday.mp4     | 14:30:00   | unknown_new
```

---

## 🎮 How To Use

### Step 1: Initialize Enhanced Database
```bash
python -m app.models.enhanced_database
```

Output:
```
Enhanced database initialized successfully!
Tables created:
  - persons (registered people)
  - unknown_persons (tracked unknowns)
  - detections (all face detections)
```

### Step 2: Start Enhanced Server
```bash
python start_enhanced.py
```

### Step 3: Process Your First Video

**Using API:**
```bash
curl -X POST "http://localhost:8000/api/v1/enhanced-video/process" \
  -F "video=@office_monday.mp4" \
  -F "save_frames=true"
```

**Response:**
```json
{
  "video_name": "office_monday.mp4",
  "total_detections": 25,
  "breakdown": {
    "registered_persons": 5,
    "tracked_unknowns": 0,
    "new_unknowns": 3
  },
  "new_unknowns_created": 3,
  "message": "Video processed! Found 5 registered persons and 3 new unknown persons."
}
```

### Step 4: Process Second Video

**Same API call:**
```bash
curl -X POST "http://localhost:8000/api/v1/enhanced-video/process" \
  -F "video=@office_tuesday.mp4"
```

**Response:**
```json
{
  "total_detections": 30,
  "breakdown": {
    "registered_persons": 8,
    "tracked_unknowns": 12,  ← Matched from Monday!
    "new_unknowns": 2
  },
  "message": "Found 8 registered persons, 12 previously seen unknowns, and 2 new unknown persons."
}
```

### Step 5: View Unknown Persons

**List all unknowns:**
```bash
curl "http://localhost:8000/api/v1/enhanced-video/unknown-persons"
```

**Response:**
```json
{
  "total": 5,
  "unknown_persons": [
    {
      "id": 1,
      "identifier": "Unknown-0001",
      "total_detections": 15,
      "first_seen": "2025-11-08 09:15:00",
      "last_seen": "2025-11-10 16:30:00",
      "representative_image_path": "detections/unknown_120_0.jpg"
    },
    {
      "id": 2,
      "identifier": "Unknown-0002",
      "total_detections": 3,
      "first_seen": "2025-11-09 14:30:00",
      "last_seen": "2025-11-09 17:45:00"
    }
  ]
}
```

### Step 6: Check Unknown Person Timeline

**See where Unknown-0001 appeared:**
```bash
curl "http://localhost:8000/api/v1/enhanced-video/unknown-persons/1/timeline"
```

**Response:**
```json
{
  "identifier": "Unknown-0001",
  "total_detections": 15,
  "videos_appeared_in": 3,
  "timeline": [
    {
      "timestamp": "2025-11-08 09:15:03",
      "video_name": "monday.mp4",
      "frame_number": 120
    },
    {
      "timestamp": "2025-11-08 09:16:45",
      "video_name": "monday.mp4",
      "frame_number": 450
    },
    {
      "timestamp": "2025-11-09 09:20:12",
      "video_name": "tuesday.mp4",
      "frame_number": 230
    }
  ]
}
```

### Step 7: Promote Unknown to Registered Person

**When you identify who Unknown-0001 is:**
```bash
curl -X POST "http://localhost:8000/api/v1/enhanced-video/unknown-persons/1/promote" \
  -F "name=Mike Johnson" \
  -F "email=mike@company.com" \
  -F "employee_id=EMP003"
```

**Response:**
```json
{
  "message": "Successfully promoted Unknown-0001 to registered person",
  "person_id": 3,
  "person_name": "Mike Johnson",
  "detections_transferred": 15
}
```

**Now all 15 past detections are linked to "Mike Johnson"!**

---

## 🎯 Real-World Scenarios

### Scenario 1: Security Monitoring
```
Week 1: Process 5 days of footage
- Registered: 50 employees recognized
- Unknown: 8 unknown persons detected

Week 2: Continue processing
- Unknown-0003 appears 15 times
- Investigation reveals: delivery person
- Promote Unknown-0003 → "John (Delivery)"

Week 3:
- System automatically recognizes delivery person
- Alert if Unknown-0003 enters restricted area
```

### Scenario 2: Investigation
```
Event: Theft on Friday

Check who was present:
1. Query all detections for Friday
2. Find 3 unknown persons
3. Check their timelines:
   - Unknown-0005: Only on Friday (suspicious!)
   - Unknown-0002: Regular visitor all week
   - Unknown-0007: First time appearance

Focus investigation on Unknown-0005
```

### Scenario 3: Visitor Management
```
Monday: Unknown person appears → Unknown-0010
Tuesday: Same person → Unknown-0010 (2 visits)
Wednesday: Same person → Unknown-0010 (3 visits)

Security identifies: Client visiting for project

Action: Promote Unknown-0010 → "Sarah (Client XYZ)"
Result: Future visits automatically recognized
```

---

## 📊 Statistics & Analytics

### Get Overall Stats
```python
# Count registered persons
SELECT COUNT(*) FROM persons WHERE is_active = 1;

# Count tracked unknowns
SELECT COUNT(*) FROM unknown_persons WHERE is_active = 1;

# Most seen unknown person
SELECT identifier, total_detections
FROM unknown_persons
ORDER BY total_detections DESC
LIMIT 10;

# Unknown persons seen in multiple videos
SELECT
    up.identifier,
    COUNT(DISTINCT d.video_name) as video_count,
    up.total_detections
FROM unknown_persons up
JOIN detections d ON d.unknown_person_id = up.id
GROUP BY up.id
HAVING video_count > 1
ORDER BY video_count DESC;
```

---

## ⚙️ Configuration

**Tolerance Settings:**
```yaml
# config.yaml (add these)

enhanced_recognition:
  registered_tolerance: 0.85    # Strict for registered persons
  unknown_tolerance: 0.80       # Slightly looser for unknowns
  min_sightings_to_track: 1     # Track after 1 sighting
  auto_cleanup_days: 30         # Remove unknowns not seen in 30 days
```

---

## 🔄 Workflow Comparison

### Basic System:
```
Video 1 → [John ✓] [Jane ✓] [Unknown ✗]
Video 2 → [John ✓] [Jane ✓] [Unknown ✗]
Video 3 → [John ✓] [Jane ✓] [Unknown ✗]

Result: Unknown faces are lost ❌
```

### Enhanced System:
```
Video 1 → [John ✓] [Jane ✓] [Unknown-0001 💾]
Video 2 → [John ✓] [Jane ✓] [Unknown-0001 ✓ (matched!)]
Video 3 → [John ✓] [Jane ✓] [Unknown-0001 ✓ (matched!)]

Result: Unknown faces are tracked! ✅
You can see: Unknown-0001 appeared 3 times across 3 videos
```

---

## 🎓 API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/enhanced-video/process` | POST | Process video with tracking |
| `/api/v1/enhanced-video/unknown-persons` | GET | List all unknown persons |
| `/api/v1/enhanced-video/unknown-persons/{id}/timeline` | GET | Get timeline for unknown person |
| `/api/v1/enhanced-video/unknown-persons/{id}/promote` | POST | Promote unknown to registered |

---

## 💡 Pro Tips

### Tip 1: Batch Processing
```bash
# Process a week of videos
for video in office_mon.mp4 office_tue.mp4 office_wed.mp4; do
  curl -X POST "http://localhost:8000/api/v1/enhanced-video/process" \
    -F "video=@$video"
done

# Then check unknowns
curl "http://localhost:8000/api/v1/enhanced-video/unknown-persons?min_detections=5"
```

### Tip 2: Periodic Review
```python
# Weekly script to review frequent unknowns
import requests

response = requests.get(
    "http://localhost:8000/api/v1/enhanced-video/unknown-persons",
    params={"min_detections": 10}  # Seen 10+ times
)

for unknown in response.json()["unknown_persons"]:
    print(f"{unknown['identifier']}: {unknown['total_detections']} times")
    # Review and promote if identified
```

### Tip 3: Alert on New Unknowns
```python
# Alert when too many new unknowns detected
result = process_video("latest.mp4")

if result["new_unknowns_created"] > 5:
    send_alert("High number of new unknown persons detected!")
```

---

## 🎉 Summary

**You now have:**
1. ✅ Cross-video face tracking
2. ✅ Automatic unknown person clustering
3. ✅ Unknown person timelines
4. ✅ Ability to promote unknowns to registered
5. ✅ Complete audit trail across all videos

**Benefits:**
- 🔍 Track suspicious persons across multiple days
- 📊 Build comprehensive visitor database automatically
- 🎯 Reduce manual registration (promote after identification)
- 📈 Better security insights over time

---

## 🚀 Get Started

```bash
# 1. Initialize database
python -m app.models.enhanced_database

# 2. Start server
python start_enhanced.py

# 3. Process videos
curl -X POST "http://localhost:8000/api/v1/enhanced-video/process" \
  -F "video=@your_video.mp4"

# 4. View tracked unknowns
curl "http://localhost:8000/api/v1/enhanced-video/unknown-persons"
```

**Happy tracking!** 🎥👤✨
