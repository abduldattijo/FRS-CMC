# How to Start the Improved System

## Current Status

✅ Configuration fixed - backward compatible with both old and new configs
⚠️ Dependency conflicts detected - need to resolve before full system works

## Quick Fix for Dependency Issues

There's a conflict between TensorFlow 2.20 (needed by RetinaFace) and MediaPipe. Here's how to fix it:

### Option 1: Use InsightFace Only (Recommended for Now)

The InsightFace recognizer works without RetinaFace. Start with just the recognition improvements:

```bash
# Install only what's needed for InsightFace
pip install insightface==0.7.3 onnxruntime==1.19.2 onnx==1.16.2

# Install FAISS for fast search
pip install faiss-cpu==1.8.0

# Download InsightFace models
python download_models.py
```

### Option 2: Full Install (Requires Fixing Dependencies)

1. **Uninstall conflicting packages**:
```bash
pip uninstall tensorflow tf-keras tensorboard mediapipe retina-face -y
```

2. **Install in correct order**:
```bash
# Install TensorFlow first
pip install tensorflow==2.17.0  # Older version compatible with more packages

# Install RetinaFace
pip install retina-face==0.0.17

# Install InsightFace
pip install insightface==0.7.3 onnxruntime==1.19.2

# Install FAISS
pip install faiss-cpu==1.8.0
```

3. **Download models**:
```bash
python download_models.py
```

---

## Start the Cross-Video System

### Using the Existing Cross-Video Server

```bash
# Start the cross-video tracking server (port 8001)
python start_cross_video.py
```

**Access**:
- Dashboard: http://localhost:8001
- API Docs: http://localhost:8001/docs

### Using the Main Server

```bash
# Start the main server (port 8000)
python run.py
```

**Access**:
- Dashboard: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Test Individual Components

### Test Configuration Loading

```bash
python -c "
from app.core.config import settings
print(f'✓ Config loaded')
print(f'  Model: {settings.FACE_MODEL}')
print(f'  Similarity threshold: {settings.SIMILARITY_THRESHOLD}')
print(f'  Embedding dimension: {settings.EMBEDDING_DIMENSION}')
print(f'  FAISS enabled: {settings.FAISS_ENABLED}')
"
```

### Test InsightFace (after installing)

```bash
python -c "
import insightface
from insightface.app import FaceAnalysis
print('✓ InsightFace available')
print(f'  Version: {insightface.__version__}')
"
```

### Test FAISS (after installing)

```bash
python -c "
import faiss
print('✓ FAISS available')
print(f'  Version: {faiss.__version__}')
"
```

---

## Use the Old System While Fixing Dependencies

The old system still works with the current setup:

```bash
# Use the original face_recognition library
python -c "
import face_recognition
import cv2
import numpy as np

# Create test image
test_img = np.zeros((100, 100, 3), dtype=np.uint8)

# Detect faces (should work)
locations = face_recognition.face_locations(test_img)
print(f'✓ Old system working')
print(f'  Detected {len(locations)} faces')
"
```

---

## Recommended Approach

**Step 1**: Get InsightFace + FAISS working first (best improvements)

```bash
# Clean install
pip uninstall -y tensorflow tf-keras tensorboard mediapipe retina-face

# Install core improvements
pip install insightface==0.7.3 onnxruntime==1.19.2 onnx==1.16.2
pip install faiss-cpu==1.8.0
pip install scikit-image==0.24.0 imutils==0.5.4

# Download models
python download_models.py
```

**Step 2**: Test the improved recognizer

```python
from app.core.improved_face_recognizer import ImprovedFaceRecognizer
import cv2
import numpy as np

# Initialize
recognizer = ImprovedFaceRecognizer(similarity_threshold=0.62)
print("✓ Improved recognizer loaded!")

# Test with image
# image = cv2.imread("test.jpg")
# embedding = recognizer.get_face_embedding(image)
# print(f"Embedding shape: {embedding.shape}")  # Should be (512,)
```

**Step 3**: Add RetinaFace later (optional)

Once the core works, you can add RetinaFace detection separately.

---

## Configuration for Current Setup

Use `config.yaml` (already updated to be backward compatible):

```yaml
face_recognition:
  model: "insightface_buffalo_l"      # Use InsightFace
  embedding_dimension: 512            # 512D embeddings
  similarity_threshold: 0.62          # Optimized threshold
  detector: "retinaface"              # Will fallback if not available

faiss:
  enabled: true                       # Use FAISS for speed
  k_neighbors: 50
```

---

## Start Commands Summary

| Command | Purpose | Port |
|---------|---------|------|
| `python run.py` | Main server | 8000 |
| `python start_cross_video.py` | Cross-video tracking | 8001 |
| `python start_enhanced.py` | Enhanced features | 8002 |
| `python download_models.py` | Download InsightFace models | - |

---

## Troubleshooting

### "No module named 'insightface'"
```bash
pip install insightface==0.7.3 onnxruntime==1.19.2
```

### "No module named 'faiss'"
```bash
pip install faiss-cpu==1.8.0
```

### "TensorFlow/protobuf conflict"
```bash
# Uninstall all conflicting packages
pip uninstall -y tensorflow tf-keras tensorboard mediapipe retina-face

# Reinstall in order
pip install tensorflow==2.17.0
pip install retina-face==0.0.17
```

### "Model not found"
```bash
python download_models.py
```

---

## Next Steps

1. **Clean dependencies**: Resolve TensorFlow/MediaPipe conflict
2. **Install InsightFace**: Get 512D embeddings working
3. **Install FAISS**: Enable fast search
4. **Download models**: Run `python download_models.py`
5. **Test system**: Upload test videos
6. **Verify accuracy**: Compare old vs new system

---

## Quick Start (Minimal)

If you just want to get started quickly with the existing system:

```bash
# Start cross-video server
python start_cross_video.py

# Open browser
open http://localhost:8001
```

The cross-video system will work with the current face_recognition library, then you can gradually upgrade to the improved models.

---

**Status**: Configuration fixed ✅, Dependencies need attention ⚠️
**Recommended**: Install InsightFace + FAISS first, add RetinaFace later
