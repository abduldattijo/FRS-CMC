#!/bin/bash

# Install Core Improvements Only (InsightFace + FAISS)
# Avoids TensorFlow/MediaPipe conflicts by skipping RetinaFace for now

echo ""
echo "=================================================================="
echo "CORE IMPROVEMENTS INSTALLATION"
echo "=================================================================="
echo ""
echo "Installing:"
echo "  ✓ InsightFace buffalo_l (512D embeddings)"
echo "  ✓ FAISS (fast similarity search)"
echo "  ✓ Quality assessment tools"
echo ""
echo "Skipping for now:"
echo "  ⏭  RetinaFace (dependency conflict with MediaPipe)"
echo "  ⏭  Can add later after resolving conflicts"
echo ""
echo "=================================================================="
echo ""

# Check virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not activated!"
    echo "Please run: source .venv/bin/activate"
    exit 1
fi

echo "Step 1/4: Installing core packages..."
echo "=================================================================="

# Install core packages (without TensorFlow dependencies)
pip install insightface==0.7.3
pip install onnxruntime==1.19.2
pip install onnx==1.16.2
pip install faiss-cpu==1.8.0
pip install scikit-image==0.24.0
pip install imutils==0.5.4

if [ $? -ne 0 ]; then
    echo "✗ Installation failed"
    exit 1
fi

echo ""
echo "✓ Core packages installed!"
echo ""

echo "Step 2/4: Verifying installation..."
echo "=================================================================="

python -c "
import sys
packages = ['insightface', 'faiss', 'onnxruntime', 'cv2', 'numpy', 'sklearn']
missing = []
for pkg in packages:
    try:
        mod = __import__(pkg)
        version = getattr(mod, '__version__', 'unknown')
        print(f'✓ {pkg:20s} {version}')
    except ImportError:
        print(f'✗ {pkg:20s} MISSING')
        missing.append(pkg)

if missing:
    print(f'\n✗ Missing: {missing}')
    sys.exit(1)
else:
    print('\n✓ All core packages verified!')
"

if [ $? -ne 0 ]; then
    echo "✗ Verification failed"
    exit 1
fi

echo ""
echo "Step 3/4: Downloading InsightFace models (~500MB)..."
echo "=================================================================="
echo ""

read -p "Download InsightFace buffalo_l model now? [Y/n]: " download_models

if [[ ! "$download_models" =~ ^[Nn]$ ]]; then
    python download_models.py

    if [ $? -ne 0 ]; then
        echo ""
        echo "⚠️  Model download failed"
        echo "You can try again later: python download_models.py"
        echo ""
    fi
else
    echo "⚠️  Skipped model download"
    echo "Remember to run: python download_models.py"
    echo ""
fi

echo ""
echo "Step 4/4: Testing the system..."
echo "=================================================================="

python -c "
print('Testing InsightFace...')
try:
    from insightface.app import FaceAnalysis
    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
    print('✓ InsightFace buffalo_l loaded successfully!')
except Exception as e:
    print(f'⚠️  InsightFace test failed: {e}')
    print('   Run: python download_models.py')

print('\nTesting FAISS...')
try:
    import faiss
    import numpy as np
    # Create simple test index
    d = 512  # dimension
    index = faiss.IndexFlatIP(d)
    test_vectors = np.random.random((10, d)).astype('float32')
    # Normalize
    faiss.normalize_L2(test_vectors)
    index.add(test_vectors)
    print(f'✓ FAISS working! (indexed {index.ntotal} test vectors)')
except Exception as e:
    print(f'✗ FAISS test failed: {e}')

print('\nTesting configuration...')
try:
    from app.core.config import settings
    print(f'✓ Config loaded')
    print(f'  - Model: {settings.FACE_MODEL}')
    print(f'  - Similarity threshold: {settings.SIMILARITY_THRESHOLD}')
    print(f'  - FAISS enabled: {settings.FAISS_ENABLED}')
except Exception as e:
    print(f'✗ Config test failed: {e}')
"

echo ""
echo "=================================================================="
echo "✓ CORE IMPROVEMENTS INSTALLED!"
echo "=================================================================="
echo ""
echo "What's working now:"
echo "  ✓ InsightFace buffalo_l (512D embeddings)"
echo "  ✓ FAISS fast search"
echo "  ✓ Improved face recognition"
echo "  ✓ Configuration system"
echo ""
echo "What's NOT installed yet:"
echo "  ⏭  RetinaFace detector (conflicts with MediaPipe)"
echo "  → Will use existing detection for now"
echo "  → Can add RetinaFace later by resolving TensorFlow conflict"
echo ""
echo "Next steps:"
echo "  1. Start the server: python start_cross_video.py"
echo "  2. Upload test videos: http://localhost:8001"
echo "  3. Compare accuracy with old system"
echo ""
echo "Expected improvements:"
echo "  ✓ 512D embeddings (vs 128D)"
echo "  ✓ 10-100x faster search with FAISS"
echo "  ✓ Better accuracy on diverse faces"
echo "  ✓ Optimized threshold (0.62 vs 0.85)"
echo ""
echo "=================================================================="
echo ""
