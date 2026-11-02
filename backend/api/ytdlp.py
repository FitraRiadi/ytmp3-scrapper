"""Pembungkus tipis untuk binary yt-dlp + ffmpeg."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from django.conf import settings

IS_WIN = os.name == "nt"

_lock = threading.RLock()
_version: str | None = None
_ffmpeg: str | None = None
_ffmpeg_checked = False

_stream_lock = threading.Lock()
_stream_cache: dict[str, tuple[str, float]] = {}
STREAM_TTL = 5 * 60 * 60  # URL googlevideo biasanya berlaku ~6 jam


# ------------------------------------------------------------------ #
# util proses
# ------------------------------------------------------------------ #
def popen_kwargs() -> dict:
    """Sembunyikan jendela console di Windows."""
    if IS_WIN:
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def ytdlp_path() -> Path:
    return Path(settings.YTDLP_BIN)


def download_url() -> str:
    if IS_WIN:
        return "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    if os.uname().sysname == "Darwin":  # pragma: no cover
        return "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"
    return "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"


def ensure_ytdlp(force: bool = False) -> Path:
    """Pastikan binary yt-dlp ada (unduh sekali kalau belum ada)."""
    path = ytdlp_path()
    with _lock:
        if path.exists() and not force:
            return path

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".download")
        print(f"[yt-dlp] mengunduh binary ke {path} ...")
        urllib.request.urlretrieve(download_url(), tmp)
        if tmp.stat().st_size < 1_000_000:
            tmp.unlink(missing_ok=True)
            raise RuntimeError("Ukuran binary yt-dlp tidak wajar, unduhan dibatalkan.")
        tmp.replace(path)
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

        global _version
        _version = None
        print("[yt-dlp] selesai.")
        return path


def version() -> str | None:
    global _version
    with _lock:
        if _version is not None:
            return _version
        try:
            out = subprocess.run(
                [str(ytdlp_path()), "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=25,
                **popen_kwargs(),
            )
            _version = (out.stdout or "").strip() or None
        except Exception:
            _version = None
        return _version


def find_ffmpeg() -> str | None:
    """Cari ffmpeg di PATH atau folder winget."""
    global _ffmpeg, _ffmpeg_checked
    with _lock:
        if _ffmpeg_checked:
            return _ffmpeg
        _ffmpeg_checked = True

        candidates = [shutil.which("ffmpeg")]
        local = os.environ.get("LOCALAPPDATA")
        if IS_WIN and local:
            candidates.append(str(Path(local) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe"))

        for candidate in candidates:
            if not candidate:
                continue
            try:
                subprocess.run(
                    [candidate, "-version"],
                    capture_output=True,
                    timeout=15,
                    **popen_kwargs(),
                )
                _ffmpeg = candidate
                break
            except Exception:
                continue
        return _ffmpeg


# ------------------------------------------------------------------ #
# pencarian
# ------------------------------------------------------------------ #
def _run(args: list[str], timeout: int = 90) -> tuple[str, str]:
    proc = subprocess.run(
        [str(ytdlp_path()), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        **popen_kwargs(),
    )
    return proc.stdout or "", proc.stderr or ""


def _normalize(entry: dict) -> dict | None:
    video_id = entry.get("id") or ""
    if not isinstance(video_id, str) or len(video_id) != 11:
        return None

    thumbs = entry.get("thumbnails") or []
    usable = [t for t in thumbs if isinstance(t, dict) and t.get("url") and (t.get("width") or 0) >= 300]
    usable.sort(key=lambda t: t.get("width") or 0, reverse=True)
    thumbnail = usable[0]["url"] if usable else f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"

    live_status = entry.get("live_status")

    return {
        "id": video_id,
        "title": entry.get("title") or entry.get("fulltitle") or "Tanpa judul",
        "channel": entry.get("channel") or entry.get("uploader") or "Unknown",
        "channelVerified": bool(entry.get("channel_is_verified")),
        "duration": int(entry.get("duration") or 0),
        "viewCount": int(entry.get("view_count") or 0),
        "thumbnail": thumbnail,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "live": bool(live_status and live_status != "not_live"),
    }


def _is_youtube_url(value: str) -> bool:
    return value.startswith(("http://", "https://")) and ("youtube.com" in value or "youtu.be" in value)


def search(query: str, limit: int = 5) -> list[dict]:
    """Cari di YouTube tanpa API key: 'ytsearchN:<query>'."""
    query = (query or "").strip()
    if not query:
        raise ValueError("Kata kunci kosong")

    limit = max(1, min(int(limit or 5), settings.MAX_RESULTS))
    is_url = _is_youtube_url(query)

    args = (
        [query, "--dump-single-json", "--no-playlist", "--no-warnings", "--no-flat-playlist"]
        if is_url
        else [f"ytsearch{limit}:{query}", "--flat-playlist", "--dump-json", "--no-warnings", "--ignore-errors"]
    )
    args += ["--socket-timeout", "20", "--extractor-retries", "2"]

    stdout, stderr = _run(args, timeout=90)
    raw = (stdout or "").strip()
    entries: list[dict] = []

    if is_url:
        try:
            payload = json.loads(raw)
            entries = payload.get("entries") or [payload]
        except json.JSONDecodeError:
            entries = []
    else:
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not entries:
        detail = " ".join((stderr or "").strip().splitlines()[-3:]) or "Tidak ada hasil dari YouTube."
        raise RuntimeError(_short_error(detail))

    results, seen = [], set()
    for entry in entries:
        item = _normalize(entry)
        if not item or item["id"] in seen:
            continue
        seen.add(item["id"])
        results.append(item)
        if len(results) >= limit:
            break
    return results


# ------------------------------------------------------------------ #
# stream langsung (tanpa file MP3)
# ------------------------------------------------------------------ #
def _url_expiry(url: str) -> float:
    """Ambil waktu kedaluwarsa dari parameter expire= milik URL googlevideo."""
    match = re.search(r"[?&]expire=(\d+)", url)
    if match:
        try:
            # sisakan margin 60 detik supaya tidak mati di tengah playback
            return max(float(match.group(1)) - 60, time.time() + 60)
        except ValueError:
            pass
    return time.time() + STREAM_TTL


def resolve_stream(video_id: str, force: bool = False) -> str:
    """Resolve URL audio langsung dari YouTube (di-cache sampai mendekati expire)."""
    video_id = (video_id or "").strip()
    if len(video_id) != 11:
        raise ValueError("ID video tidak valid")

    now = time.time()
    with _stream_lock:
        cached = _stream_cache.get(video_id)
        if cached and not force and cached[1] > now:
            return cached[0]
        # buang entri kedaluwarsa lain sekalian
        for key, (_, expires_at) in list(_stream_cache.items()):
            if expires_at <= now:
                _stream_cache.pop(key, None)

    stdout, stderr = _run(
        [
            f"https://www.youtube.com/watch?v={video_id}",
            "-f",
            "bestaudio[ext=m4a]/bestaudio",
            "--no-playlist",
            "--no-warnings",
            "-g",
            "--socket-timeout",
            "20",
            "--extractor-retries",
            "2",
        ],
        timeout=60,
    )

    url = next(
        (line.strip() for line in (stdout or "").splitlines() if line.strip().startswith("http")),
        "",
    )
    if not url:
        detail = " ".join((stderr or "").strip().splitlines()[-3:]) or "Tidak ada URL audio."
        raise RuntimeError(_short_error(detail))

    with _stream_lock:
        _stream_cache[video_id] = (url, _url_expiry(url))
    return url


def clear_stream_cache(video_id: str | None = None) -> None:
    with _stream_lock:
        if video_id:
            _stream_cache.pop(video_id, None)
        else:
            _stream_cache.clear()


def _short_error(text: str) -> str:
    text = (text or "").replace("ERROR:", "").strip()
    if any(k in text.lower() for k in ("sign in to confirm", "bot", "403")):
        return "YouTube menolak permintaan (bot check). Coba lagi atau update yt-dlp."
    return text[:300] or "yt-dlp gagal tanpa pesan."
