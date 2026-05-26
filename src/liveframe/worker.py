"""Cloud Run Job worker — runs a single video processing job to completion.

Reads configuration from environment variables, downloads the video from GCS
or a URL (Twitch/YouTube via yt-dlp), runs the pipeline, uploads clips to GCS,
and writes results to Supabase.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("liveframe.worker")


def download_from_gcs(gcs_uri: str) -> Path:
    """Download a gs:// URI to a local temp file."""
    from google.cloud import storage as gcs

    parts = gcs_uri.replace("gs://", "").split("/", 1)
    bucket_name, object_name = parts[0], parts[1]

    client = gcs.Client()
    blob = client.bucket(bucket_name).blob(object_name)

    suffix = Path(object_name).suffix or ".mp4"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="liveframe_dl_")
    blob.download_to_filename(tmp.name)
    logger.info("Downloaded %s to %s (%.1f MB)", gcs_uri, tmp.name, Path(tmp.name).stat().st_size / 1e6)
    return Path(tmp.name)


def download_from_url(url: str) -> Path:
    """Download a video from a URL (Twitch/YouTube/etc.) using yt-dlp."""
    output_path = Path(tempfile.mkdtemp(prefix="liveframe_ytdl_")) / "video.mp4"

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--merge-output-format",
        "mp4",
        "-o",
        str(output_path),
        url,
    ]

    logger.info("Downloading from URL: %s", url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

    if result.returncode != 0:
        error_msg = result.stderr.strip().split("\n")[-1] if result.stderr else "yt-dlp failed"
        raise RuntimeError(f"Download failed: {error_msg}")

    if not output_path.exists():
        raise RuntimeError("Download completed but output file not found")

    logger.info("Downloaded %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)
    return output_path


def is_url(path: str) -> bool:
    """Check if the input path is a URL (not a GCS path or local file)."""
    return path.startswith("http://") or path.startswith("https://")


def upload_clips_to_gcs(job_id: str, output_dir: Path) -> dict[str, str]:
    """Upload all clips in output_dir to GCS. Returns {local_name: gs_path}."""
    from google.cloud import storage as gcs

    bucket_name = os.environ.get("GCS_BUCKET", "liveframe-uploads")
    client = gcs.Client()
    bucket = client.bucket(bucket_name)
    uploaded = {}

    for clip_file in output_dir.glob("clip_*.mp4"):
        object_name = f"clips/{job_id}/{clip_file.name}"
        blob = bucket.blob(object_name)
        blob.upload_from_filename(str(clip_file))
        gcs_path = f"gs://{bucket_name}/{object_name}"
        uploaded[clip_file.name] = gcs_path
        logger.info("Uploaded %s -> %s", clip_file.name, gcs_path)

    return uploaded


def update_supabase(job_id: str, updates: dict):
    """Update job row in Supabase."""
    from supabase import create_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    client = create_client(url, key)
    client.table("jobs").update(updates).eq("id", job_id).execute()


async def run_job():
    """Main worker entry point."""
    # Read config from environment
    job_id = os.environ["JOB_ID"]
    input_path = os.environ["INPUT_PATH"]
    gemini_key = os.environ["GEMINI_API_KEY"]
    preset_str = os.environ.get("PRESET", "general")
    criteria = os.environ.get("CRITERIA") or None
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    analysis_mode = os.environ.get("ANALYSIS_MODE", "fast")
    clips_per_hour = float(os.environ.get("CLIPS_PER_HOUR", "2.5"))
    min_clip_seconds = float(os.environ.get("MIN_CLIP_SECONDS", "15"))
    margin_seconds = float(os.environ.get("MARGIN_SECONDS", "3"))

    logger.info("Worker starting job %s: %s (preset=%s, model=%s)", job_id, input_path, preset_str, gemini_model)

    # Update status to analyzing
    update_supabase(job_id, {"status": "analyzing", "progress": {"current_step": "Starting..."}})

    # Download video from GCS, URL, or use local path
    local_input = None
    if input_path.startswith("gs://"):
        update_supabase(job_id, {"progress": {"current_step": "Downloading video from cloud..."}})
        try:
            local_input = download_from_gcs(input_path)
        except Exception as e:
            logger.error("GCS download failed: %s", e)
            update_supabase(
                job_id,
                {
                    "status": "failed",
                    "error": f"Download failed: {e}",
                    "progress": {"current_step": "Failed"},
                },
            )
            return
    elif is_url(input_path):
        update_supabase(job_id, {"progress": {"current_step": "Downloading video from URL..."}})
        try:
            local_input = download_from_url(input_path)
        except Exception as e:
            logger.error("URL download failed: %s", e)
            update_supabase(
                job_id,
                {
                    "status": "failed",
                    "error": f"Download failed: {e}",
                    "progress": {"current_step": "Failed"},
                },
            )
            return

    resolved_input = local_input or Path(input_path)

    # Build settings
    from liveframe.config import AnalysisMode, GeminiModel, LiveframeSettings, PresetCriteria

    settings = LiveframeSettings(
        gemini_api_key=gemini_key,
        gemini_model=GeminiModel(gemini_model),
        analysis_mode=AnalysisMode(analysis_mode),
        target_clips_per_hour=clips_per_hour,
        min_clip_seconds=min_clip_seconds,
        margin_seconds=margin_seconds,
    )

    preset = None
    try:
        preset = PresetCriteria(preset_str)
    except ValueError:
        pass

    output_dir = Path(f"/tmp/liveframe_output/{job_id}")

    # Run pipeline
    from liveframe.core.pipeline import process_video
    from liveframe.models import JobStatus

    try:
        async for event in process_video(
            input_path=resolved_input,
            settings=settings,
            criteria=criteria,
            preset=preset,
            output_dir=output_dir,
        ):
            # Sync progress to Supabase
            progress_data = {
                "current_step": event.current_step,
                "chunks_total": event.chunks_total,
                "chunks_completed": event.chunks_completed,
                "highlights_found": event.highlights_found,
                "clips_extracted": event.clips_extracted,
                "clips_total": event.clips_total,
            }

            updates: dict = {"progress": progress_data}

            if event.status == JobStatus.ANALYZING:
                updates["status"] = "analyzing"
            elif event.status == JobStatus.EXTRACTING:
                updates["status"] = "extracting"

            # Sync highlights when available
            if event.status in (JobStatus.EXTRACTING, JobStatus.COMPLETED):
                manifest_path = output_dir / "manifest.json"
                if manifest_path.exists():
                    manifest = json.loads(manifest_path.read_text())
                    updates["highlights"] = manifest.get("highlights", [])

            update_supabase(job_id, updates)

            if event.status == JobStatus.FAILED:
                update_supabase(
                    job_id,
                    {
                        "status": "failed",
                        "error": event.error or "Unknown error",
                        "progress": progress_data,
                    },
                )
                return

        # Upload clips to GCS
        if output_dir.exists():
            update_supabase(job_id, {"progress": {"current_step": "Uploading clips..."}})
            uploaded = upload_clips_to_gcs(job_id, output_dir)

            # Read final manifest for clips metadata
            manifest_path = output_dir / "manifest.json"
            clips_data = []
            highlights_data = []
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text())
                highlights_data = manifest.get("highlights", [])
                for clip in manifest.get("clips", []):
                    clip_name = Path(clip["output_path"]).name
                    if clip_name in uploaded:
                        clip["output_path"] = uploaded[clip_name]
                    clips_data.append(clip)

            update_supabase(
                job_id,
                {
                    "status": "completed",
                    "highlights": highlights_data,
                    "clips": clips_data,
                    "progress": {"current_step": "Complete"},
                    "error": None,
                },
            )
            logger.info("Job %s completed: %d highlights, %d clips", job_id, len(highlights_data), len(clips_data))
        else:
            update_supabase(
                job_id,
                {
                    "status": "completed",
                    "progress": {"current_step": "Complete (no clips)"},
                },
            )

    except Exception as e:
        logger.error("Job %s failed: %s", job_id, e, exc_info=True)
        update_supabase(
            job_id,
            {
                "status": "failed",
                "error": str(e),
                "progress": {"current_step": "Failed"},
            },
        )
    finally:
        # Clean up temp files
        if local_input and local_input.exists():
            local_input.unlink(missing_ok=True)
        logger.info("Worker finished job %s", job_id)


def main():
    asyncio.run(run_job())


if __name__ == "__main__":
    main()
