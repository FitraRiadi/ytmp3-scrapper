"""Manajemen job konversi (in-memory) + simpan riwayat ke database."""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from django.conf import settings

from . import storage, ytdlp
from .models import Track

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
PROGRESS_RE = re.compile(r"^\[download\]\s+(\d+(?:\.\d+)?)%")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

_lock = threading.RLock()
_jobs: dict[str, dict] = {}
_executor: ThreadPoolExecutor | None = None


def bootstrap() -> None:
    """Dipanggil sekali dari AppConfig.ready()."""
    global _executor
    with _lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=max(1, int(settings.MAX_CONCURRENT_JOBS)),
                thread_name_prefix="ytmp3",
            )


# ------------------------------------------------------------------ #
# helper
# ------------------------------------------------------------------ #
def mp3_path(video_id: str) -> Path:
    return storage.download_dir() / f"{video_id}.mp3"


def job_mp3_path(job: dict) -> Path:
    """Path file untuk satu job (folder dikunci saat job dibuat)."""
    out_dir = job.get("out_dir")
    return Path(out_dir) / f"{job['id']}.mp3" if out_dir else mp3_path(job["id"])


def safe_file_name(value: str, fallback: str = "audio", max_len: int = 120) -> str:
    value = re.sub(r'[\x00-\x1f<>:"/\\|?*]+', " ", str(value or ""))
    value = re.sub(r"\s+", " ", value).strip().rstrip(". ")
    return (value or fallback)[:max_len]


def build_file_name(title: str, channel: str, video_id: str) -> str:
    title = (title or "").strip()
    channel = (channel or "").strip()
    if channel and title.lower().startswith(channel.lower()):
        base = title
    elif channel:
        base = f"{channel} - {title}"
    else:
        base = title
    return f"{safe_file_name(base, video_id)}.mp3"


def human_size(size: int) -> str:
    size = int(size or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def public_job(job: dict) -> dict:
    ready = job.get("status") == "ready"
    return {
        "id": job["id"],
        "title": job.get("title", ""),
        "channel": job.get("channel", ""),
        "duration": job.get("duration", 0),
        "thumbnail": job.get("thumbnail", ""),
        "status": job.get("status", "queued"),
        "progress": int(round(job.get("progress", 0))),
        "message": job.get("message", ""),
        "size": job.get("size", 0),
        "sizeLabel": human_size(job["size"]) if job.get("size") else None,
        "fileName": job.get("file_name", ""),
        "error": job.get("error"),
        "cached": bool(job.get("cached")),
        "mediaUrl": f"/api/media/{job['id']}" if ready else None,
        "downloadUrl": f"/api/media/{job['id']}?download=1" if ready else None,
    }


def serialize_track(track: Track) -> dict:
    return {
        "id": track.video_id,
        "title": track.title,
        "channel": track.channel,
        "duration": track.duration,
        "thumbnail": track.thumbnail,
        "status": "ready",
        "progress": 100,
        "message": "Selesai",
        "size": track.file_size,
        "sizeLabel": human_size(track.file_size),
        "fileName": track.file_name,
        "error": None,
        "cached": True,
        "mediaUrl": f"/api/media/{track.video_id}",
        "downloadUrl": f"/api/media/{track.video_id}?download=1",
        "createdAt": track.created_at.isoformat(),
    }


# ------------------------------------------------------------------ #
# API job
# ------------------------------------------------------------------ #
def create_job(payload: dict) -> dict:
    bootstrap()
    video_id = str(payload.get("id") or "").strip()
    if not VIDEO_ID_RE.match(video_id):
        raise ValueError("ID video tidak valid")

    with _lock:
        existing = _jobs.get(video_id)
        if existing and existing["status"] != "error":
            return public_job(existing)

    title = str(payload.get("title") or "audio")[:300]
    channel = str(payload.get("channel") or "Unknown")[:200]
    duration = int(payload.get("duration") or 0)
    thumbnail = str(payload.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg")

    out_dir = storage.download_dir()
    file_name = build_file_name(title, channel, video_id)
    path = out_dir / f"{video_id}.mp3"

    # sudah pernah dikonversi? (file di disk = cache tercepat)
    if path.exists() and path.stat().st_size > 1024:
        track = Track.objects.filter(video_id=video_id).first()
        if track:
            file_name = track.file_name or file_name
            title = track.title or title
            channel = track.channel or channel
            duration = track.duration or duration
            thumbnail = track.thumbnail or thumbnail
        job = {
            "id": video_id,
            "title": title,
            "channel": channel,
            "duration": duration,
            "thumbnail": thumbnail,
            "status": "ready",
            "progress": 100,
            "message": "Sudah tersedia (cache)",
            "size": path.stat().st_size,
            "file_name": file_name,
            "error": None,
            "cached": True,
            "canceled": False,
            "process": None,
            "out_dir": str(out_dir),
            "started_at": time.time(),
        }
        with _lock:
            _jobs[video_id] = job
        _persist(job)
        return public_job(job)

    job = {
        "id": video_id,
        "title": title,
        "channel": channel,
        "duration": duration,
        "thumbnail": thumbnail,
        "status": "queued",
        "progress": 0,
        "message": "Menunggu antrian...",
        "size": 0,
        "file_name": file_name,
        "error": None,
        "cached": False,
        "canceled": False,
        "process": None,
        "out_dir": str(out_dir),
        "started_at": time.time(),
    }
    with _lock:
        _jobs[video_id] = job
        _cleanup_locked()

    assert _executor is not None
    _executor.submit(_run, job)
    return public_job(job)


def get_job(video_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(video_id)
        return public_job(job) if job else None


def list_jobs() -> list[dict]:
    with _lock:
        return [public_job(job) for job in _jobs.values()]


def cancel_job(video_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(video_id)
        if not job:
            return None
        if job["status"] == "ready":
            return public_job(job)
        job["canceled"] = True
        job["status"] = "error"
        job["error"] = "Dibatalkan"
        job["message"] = "Dibatalkan"
        proc = job.get("process")

    if proc and proc.poll() is None:
        _kill_tree(proc)
    return public_job(job)


def _kill_tree(proc: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                **ytdlp.popen_kwargs(),
            )
        else:
            proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _cleanup_locked() -> None:
    """Buang job lama yang sudah selesai supaya memori tidak menumpuk."""
    now = time.time()
    for key, job in list(_jobs.items()):
        if job["status"] in ("ready", "error") and now - job.get("started_at", now) > 3 * 3600:
            _jobs.pop(key, None)


# ------------------------------------------------------------------ #
# worker konversi
# ------------------------------------------------------------------ #
def _run(job: dict) -> None:
    video_id = job["id"]

    if job.get("canceled"):
        job["status"] = "error"
        job["message"] = "Dibatalkan"
        return

    ffmpeg = ytdlp.find_ffmpeg()
    out_dir = Path(job.get("out_dir") or storage.download_dir())
    out_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(out_dir / f"{video_id}.%(ext)s")

    args = [
        str(ytdlp.ytdlp_path()),
        "-f", "bestaudio/best",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--embed-metadata",
        "--no-playlist",
        "--no-mtime",
        "--newline",
        "--no-warnings",
        "--concurrent-fragments", "4",
        "--socket-timeout", "20",
        "--retries", "5",
    ]
    if ffmpeg and ffmpeg != "ffmpeg":
        args += ["--ffmpeg-location", ffmpeg]
    args += ["-o", out_template, "--", f"https://www.youtube.com/watch?v={video_id}"]

    job["status"] = "downloading"
    job["progress"] = 1
    job["message"] = "Mengambil audio dari YouTube..."

    tail: list[str] = []
    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            **ytdlp.popen_kwargs(),
        )
    except Exception as exc:  # noqa: BLE001
        job["status"] = "error"
        job["error"] = f"Tidak bisa menjalankan yt-dlp: {exc}"
        job["message"] = "Gagal"
        return

    job["process"] = proc
    assert proc.stdout is not None
    for raw in proc.stdout:
        line = ANSI_RE.sub("", raw).strip()
        if not line:
            continue
        tail.append(line)
        del tail[:-40]

        match = PROGRESS_RE.match(line)
        if match:
            pct = float(match.group(1))
            job["progress"] = max(job["progress"], min(85.0, pct * 0.85))
            job["status"] = "downloading"
            job["message"] = f"Mengunduh audio... {pct:.1f}%"
            continue
        if any(tag in line for tag in ("[ExtractAudio]", "[ffmpeg]", "[Metadata]")):
            job["status"] = "converting"
            job["progress"] = max(job["progress"], 88)
            job["message"] = "Convert ke MP3..."
            continue
        if "[download] Destination:" in line:
            job["message"] = "Mengunduh audio..."

    code = proc.wait()
    job["process"] = None

    if job.get("canceled"):
        job["status"] = "error"
        job["error"] = "Dibatalkan"
        job["message"] = "Dibatalkan"
        job_mp3_path(job).unlink(missing_ok=True)
        return

    path = job_mp3_path(job)
    if code == 0 and path.exists() and path.stat().st_size > 1024:
        size = path.stat().st_size
        job["status"] = "ready"
        job["progress"] = 100
        job["message"] = "Selesai"
        job["size"] = size
        job["error"] = None
        _persist(job)
        return

    job["status"] = "error"
    job["progress"] = 0
    job["error"] = ytdlp._short_error(" ".join(tail[-6:])) if tail else f"yt-dlp gagal (exit code {code})"
    job["message"] = "Gagal convert"
    path.unlink(missing_ok=True)


def _persist(job: dict) -> None:
    """Simpan hasil konversi ke PostgreSQL + sidecar JSON di samping MP3."""
    created_at = None
    try:
        track, _ = Track.objects.update_or_create(
            video_id=job["id"],
            defaults={
                "title": job["title"],
                "channel": job["channel"],
                "duration": job["duration"],
                "thumbnail": job["thumbnail"],
                "file_name": job["file_name"],
                "file_size": job["size"],
            },
        )
        created_at = track.created_at.isoformat()
    except Exception as exc:  # noqa: BLE001
        print(f"[db] gagal menyimpan riwayat {job['id']}: {exc}")

    try:
        path = job_mp3_path(job)
        storage.write_sidecar(
            job,
            created_at=created_at,
            directory=path.parent if path.exists() else None,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[sidecar] gagal menulis metadata {job['id']}: {exc}")
