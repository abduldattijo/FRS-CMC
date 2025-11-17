"""
API routes for cross-video identity linking system
Intelligence/surveillance functionality for tracking persons across multiple videos
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import os
from pathlib import Path
import shutil

from ...models.cross_video_database import (
    SessionLocal,
    Video,
    VideoFace,
    PersonCluster,
    CrossVideoMatch,
    AnalysisJob
)
from ...core.cross_video_processor import CrossVideoProcessor
from ...core.cross_video_matcher import CrossVideoMatcher
from datetime import datetime
import json

router = APIRouter(prefix="/api/v1/cross-video", tags=["Cross-Video Analysis"])


# Pydantic models for request bodies
class AnalysisRequest(BaseModel):
    video_ids: Optional[List[int]] = None
    similarity_threshold: float = 0.85
    clustering_threshold: float = 0.90


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/upload-video")
async def upload_and_process_video(
    video: UploadFile = File(...),
    frame_skip: int = Form(5),
    save_frames: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Upload and process a video for cross-video analysis

    This endpoint:
    1. Saves the uploaded video
    2. Detects all faces in the video
    3. Clusters faces to identify unique individuals
    4. Saves VideoFace entries to database

    Later, use the /analyze endpoint to find matches across videos
    """
    # Validate file type
    allowed_extensions = [".mp4", ".avi", ".mov", ".mkv"]
    file_ext = os.path.splitext(video.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Create upload directory
    upload_dir = "data/cross_video_uploads"
    Path(upload_dir).mkdir(parents=True, exist_ok=True)

    # Save uploaded file
    video_path = os.path.join(upload_dir, video.filename)

    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    # Process the video
    try:
        processor = CrossVideoProcessor()

        result = processor.process_video(
            video_path=video_path,
            db=db,
            frame_skip=frame_skip,
            save_frames=save_frames
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Video processed successfully! Found {result['unique_faces']} unique individuals.",
                "video_id": result["video_id"],
                "video_filename": result["video_filename"],
                "total_detections": result["total_detections"],
                "unique_faces": result["unique_faces"],
                "faces": result["faces"],
                "processing_time_seconds": result["processing_time_seconds"]
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")


@router.get("/videos")
async def list_videos(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all uploaded videos with their processing status
    """
    query = db.query(Video)

    if status:
        query = query.filter(Video.processing_status == status)

    videos = query.order_by(Video.uploaded_at.desc()).all()

    return {
        "total": len(videos),
        "videos": [
            {
                "id": v.id,
                "filename": v.filename,
                "status": v.processing_status,
                "uploaded_at": v.uploaded_at.isoformat() if v.uploaded_at else None,
                "duration_seconds": v.duration_seconds,
                "total_faces_detected": v.total_faces_detected,
                "unique_faces_count": v.unique_faces_count,
            }
            for v in videos
        ]
    }


@router.get("/videos/{video_id}")
async def get_video_details(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific video
    """
    video = db.query(Video).filter(Video.id == video_id).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Get all faces in this video
    faces = db.query(VideoFace).filter(VideoFace.video_id == video_id).all()

    return {
        "id": video.id,
        "filename": video.filename,
        "filepath": video.filepath,
        "status": video.processing_status,
        "duration_seconds": video.duration_seconds,
        "fps": video.fps,
        "total_frames": video.total_frames,
        "total_faces_detected": video.total_faces_detected,
        "unique_faces_count": video.unique_faces_count,
        "uploaded_at": video.uploaded_at.isoformat() if video.uploaded_at else None,
        "processing_completed_at": video.processing_completed_at.isoformat() if video.processing_completed_at else None,
        "faces": [
            {
                "id": f.id,
                "identifier": f.face_identifier,
                "appearance_count": f.appearance_count,
                "first_frame": f.first_frame,
                "last_frame": f.last_frame,
                "average_confidence": f.average_confidence,
                "cluster_id": f.cluster_id,
                "representative_image": f.representative_image_path
            }
            for f in faces
        ]
    }


@router.post("/analyze")
async def run_cross_video_analysis(
    request: AnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Run cross-video analysis to find matching persons across different videos

    This is the core intelligence function:
    - Compares faces ONLY across different videos (never A vs A)
    - Creates PersonClusters grouping the same person across videos
    - Results show: "Person X appears in videos A, C, E"

    Args:
        request: AnalysisRequest with video_ids, similarity_threshold, clustering_threshold
    """
    # Create analysis job
    job = AnalysisJob(
        job_name=f"Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        video_ids=json.dumps(request.video_ids) if request.video_ids else None,
        similarity_threshold=request.similarity_threshold,
        clustering_threshold=request.clustering_threshold,
        status="running",
        started_at=datetime.utcnow()
    )
    db.add(job)
    db.commit()

    try:
        # Initialize matcher
        matcher = CrossVideoMatcher(
            similarity_threshold=request.similarity_threshold,
            clustering_threshold=request.clustering_threshold
        )

        # Find matches
        match_result = matcher.find_cross_video_matches(
            db=db,
            video_ids=request.video_ids,
            save_matches=True
        )

        # Build clusters
        cluster_result = matcher.build_person_clusters(
            db=db,
            video_ids=request.video_ids
        )

        # Update job
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.processing_time_seconds = (job.completed_at - job.started_at).total_seconds()
        job.total_comparisons = match_result["total_comparisons"]
        job.total_matches_found = match_result["total_matches"]
        job.total_clusters_created = cluster_result["total_clusters"]
        db.commit()

        return {
            "success": True,
            "job_id": job.id,
            "analysis_results": {
                "total_videos_analyzed": match_result["total_videos"],
                "total_faces_compared": match_result["total_faces"],
                "total_comparisons": match_result["total_comparisons"],
                "total_matches_found": match_result["total_matches"],
                "total_person_clusters": cluster_result["total_clusters"],
                "total_faces_clustered": cluster_result["total_faces_clustered"],
            },
            "processing_time_seconds": job.processing_time_seconds,
            "clusters": cluster_result["clusters"]
        }

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()

        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/clusters")
async def list_person_clusters(
    min_videos: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List all person clusters (individuals tracked across videos)

    Args:
        min_videos: Only return persons appearing in at least N videos
    """
    query = db.query(PersonCluster).filter(PersonCluster.is_active == 1)

    if min_videos:
        query = query.filter(PersonCluster.total_videos >= min_videos)

    clusters = query.order_by(PersonCluster.total_videos.desc()).all()

    return {
        "total_clusters": len(clusters),
        "clusters": [
            {
                "id": c.id,
                "identifier": c.cluster_identifier,
                "total_videos": c.total_videos,
                "total_appearances": c.total_appearances,
                "first_seen": c.first_seen_at.isoformat() if c.first_seen_at else None,
                "last_seen": c.last_seen_at.isoformat() if c.last_seen_at else None,
                "identified_name": c.identified_name,
                "representative_image": c.representative_image_path
            }
            for c in clusters
        ]
    }


@router.get("/clusters/{cluster_id}")
async def get_cluster_details(
    cluster_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a person cluster

    Shows which videos this person appears in, when, and how many times
    """
    matcher = CrossVideoMatcher()
    result = matcher.get_cluster_summary(db, cluster_id)

    if not result:
        raise HTTPException(status_code=404, detail="Cluster not found")

    return result


@router.post("/clusters/{cluster_id}/identify")
async def identify_cluster(
    cluster_id: int,
    name: str = Form(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Manually identify a person cluster

    Use this when you've determined who a tracked person is
    """
    cluster = db.query(PersonCluster).filter(PersonCluster.id == cluster_id).first()

    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster.identified_name = name
    if notes:
        cluster.notes = notes

    db.commit()

    return {
        "success": True,
        "message": f"Cluster {cluster.cluster_identifier} identified as {name}",
        "cluster_id": cluster.id,
        "cluster_identifier": cluster.cluster_identifier,
        "identified_name": cluster.identified_name
    }


@router.get("/matches")
async def get_cross_video_matches(
    min_similarity: float = 0.85,
    confirmed_only: bool = False,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get cross-video face matches

    Returns pairs of faces from different videos that match
    """
    query = db.query(CrossVideoMatch).filter(
        CrossVideoMatch.similarity_score >= min_similarity
    )

    if confirmed_only:
        query = query.filter(CrossVideoMatch.is_confirmed == 1)

    matches = query.order_by(CrossVideoMatch.similarity_score.desc()).limit(limit).all()

    # Enrich with face details
    results = []
    for match in matches:
        source_face = db.query(VideoFace).filter(VideoFace.id == match.source_face_id).first()
        target_face = db.query(VideoFace).filter(VideoFace.id == match.target_face_id).first()

        if source_face and target_face:
            results.append({
                "match_id": match.id,
                "similarity_score": match.similarity_score,
                "in_same_cluster": bool(match.in_same_cluster),
                "source_face": {
                    "id": source_face.id,
                    "identifier": source_face.face_identifier,
                    "video_id": source_face.video_id,
                    "image": source_face.representative_image_path
                },
                "target_face": {
                    "id": target_face.id,
                    "identifier": target_face.face_identifier,
                    "video_id": target_face.video_id,
                    "image": target_face.representative_image_path
                }
            })

    return {
        "total_matches": len(results),
        "matches": results
    }


@router.get("/jobs")
async def list_analysis_jobs(
    db: Session = Depends(get_db)
):
    """
    List all cross-video analysis jobs
    """
    jobs = db.query(AnalysisJob).order_by(AnalysisJob.created_at.desc()).all()

    return {
        "total_jobs": len(jobs),
        "jobs": [
            {
                "id": j.id,
                "job_name": j.job_name,
                "status": j.status,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "processing_time_seconds": j.processing_time_seconds,
                "total_comparisons": j.total_comparisons,
                "total_matches_found": j.total_matches_found,
                "total_clusters_created": j.total_clusters_created,
            }
            for j in jobs
        ]
    }


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a video and all associated data
    """
    video = db.query(Video).filter(Video.id == video_id).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Delete video file if it exists
    if os.path.exists(video.filepath):
        os.remove(video.filepath)

    # Delete database record (cascade will delete VideoFaces and RawDetections)
    db.delete(video)
    db.commit()

    return {
        "success": True,
        "message": f"Video {video.filename} deleted successfully"
    }
