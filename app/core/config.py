"""
Configuration management for the application
"""

import yaml
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from config.yaml and environment variables"""

    def __init__(self):
        # Get the project root directory
        self.BASE_DIR = Path(__file__).parent.parent.parent

        # Load YAML configuration
        config_path = self.BASE_DIR / "config.yaml"
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        # Application settings
        self.APP_NAME = self.config["app"]["name"]
        self.VERSION = self.config["app"]["version"]
        self.DEBUG = self.config["app"]["debug"]
        self.HOST = self.config["app"]["host"]
        self.PORT = self.config["app"]["port"]

        # Database
        self.DATABASE_URL = self.config["database"]["url"]
        self.DATABASE_ECHO = self.config["database"]["echo"]

        # Face Recognition (backward compatible with old and new config)
        self.FACE_MODEL = self.config["face_recognition"].get("model", "mediapipe")

        # Support both old (tolerance) and new (similarity_threshold) config
        self.FACE_TOLERANCE = self.config["face_recognition"].get(
            "tolerance",
            1.0 - self.config["face_recognition"].get("similarity_threshold", 0.62)
        )
        self.SIMILARITY_THRESHOLD = self.config["face_recognition"].get("similarity_threshold", 0.62)

        self.NUM_JITTERS = self.config["face_recognition"].get("num_jitters", 1)
        self.DETECTION_METHOD = self.config["face_recognition"].get("detection_method", "mediapipe")
        self.DETECTOR = self.config["face_recognition"].get("detector", "mediapipe")

        # New improved settings
        self.EMBEDDING_DIMENSION = self.config["face_recognition"].get("embedding_dimension", 128)
        self.DETECTION_CONFIDENCE = self.config["face_recognition"].get("detection_confidence", 0.9)
        self.CLUSTERING_THRESHOLD = self.config["face_recognition"].get("clustering_threshold", 0.65)
        self.MIN_QUALITY_SCORE = self.config["face_recognition"].get("min_quality_score", 0.5)

        # Video Processing
        self.FRAME_SKIP = self.config["video"]["frame_skip"]
        self.MAX_UPLOAD_SIZE_MB = self.config["video"]["max_upload_size_mb"]
        self.SUPPORTED_FORMATS = self.config["video"]["supported_formats"]
        self.OUTPUT_FORMAT = self.config["video"]["output_format"]
        self.RESIZE_WIDTH = self.config["video"]["resize_width"]

        # Detection (backward compatible)
        self.SAVE_DETECTIONS = self.config["detection"].get("save_detections", True)
        self.SAVE_FRAMES = self.config["detection"].get("save_frames", True)
        self.CONFIDENCE_THRESHOLD = self.config["detection"].get("confidence_threshold", 0.5)
        self.MIN_FACE_SIZE = self.config["detection"].get("min_face_size", 20)
        self.SAVE_QUALITY_SCORES = self.config["detection"].get("save_quality_scores", False)
        self.MIN_DETECTION_CONFIDENCE = self.config["detection"].get("min_detection_confidence", 0.5)

        # Paths
        self.UPLOADS_DIR = self.BASE_DIR / self.config["paths"]["uploads"]
        self.KNOWN_FACES_DIR = self.BASE_DIR / self.config["paths"]["known_faces"]
        self.DETECTIONS_DIR = self.BASE_DIR / self.config["paths"]["detections"]
        self.DATABASE_DIR = self.BASE_DIR / self.config["paths"]["database"]

        # New paths for improved system
        self.MODELS_DIR = self.BASE_DIR / self.config["paths"].get("models", "data/models")
        self.FAISS_INDEX_DIR = self.BASE_DIR / self.config["paths"].get("faiss_index", "data/faiss_index")

        # FAISS Configuration (if available)
        if "faiss" in self.config:
            self.FAISS_ENABLED = self.config["faiss"].get("enabled", False)
            self.FAISS_USE_GPU = self.config["faiss"].get("use_gpu", False)
            self.FAISS_K_NEIGHBORS = self.config["faiss"].get("k_neighbors", 50)
            self.FAISS_SAVE_INDEX = self.config["faiss"].get("save_index", True)
            self.FAISS_INDEX_PATH = self.config["faiss"].get("index_path", "data/faiss_index")
        else:
            self.FAISS_ENABLED = False
            self.FAISS_USE_GPU = False
            self.FAISS_K_NEIGHBORS = 50
            self.FAISS_SAVE_INDEX = True
            self.FAISS_INDEX_PATH = "data/faiss_index"

        # West African Optimization (if available)
        if "west_african_optimization" in self.config:
            self.WA_OPTIMIZATION_ENABLED = self.config["west_african_optimization"].get("enabled", False)
            self.WA_ENHANCE_DARK = self.config["west_african_optimization"].get("enhance_dark_regions", False)
            self.WA_ADAPTIVE_HISTOGRAM = self.config["west_african_optimization"].get("adaptive_histogram", False)
            self.WA_SHADOW_COMPENSATION = self.config["west_african_optimization"].get("shadow_compensation", 1.0)
        else:
            self.WA_OPTIMIZATION_ENABLED = False
            self.WA_ENHANCE_DARK = False
            self.WA_ADAPTIVE_HISTOGRAM = False
            self.WA_SHADOW_COMPENSATION = 1.0

        # Create directories if they don't exist
        self._ensure_directories()

        # Environment variables (overrides)
        self.SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    def _ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.UPLOADS_DIR,
            self.KNOWN_FACES_DIR,
            self.DETECTIONS_DIR,
            self.DATABASE_DIR,
            self.MODELS_DIR,
            self.FAISS_INDEX_DIR,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def get_database_url(self):
        """Get database URL with absolute path for SQLite"""
        if self.DATABASE_URL.startswith("sqlite:///"):
            # Make sure SQLite path is absolute
            db_path = self.DATABASE_URL.replace("sqlite:///", "")
            if not db_path.startswith("/"):
                db_path = str(self.BASE_DIR / db_path)
            return f"sqlite:///{db_path}"
        return self.DATABASE_URL


# Global settings instance
settings = Settings()
