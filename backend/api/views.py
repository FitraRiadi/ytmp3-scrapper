from __future__ import annotations

import json
import mimetypes
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseNotAllowed,
    JsonResponse,
    StreamingHttpResponse,
)
from django.utils.http import content_disposition_header
from django.views.decorators.csrf import csrf_exempt

from . import jobs, storage, ytdlp
from .models import Track

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
CHUNK = 64 * 1024


def _json_body(request) -> dict:
    if not request.body:
        return {}
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("JSON tidak valid") from exc
    if not isinstance(data, dict):
        raise ValueError("Body harus berupa objek JSON")
    return data


def _error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


def _ok(data: dict, status: int = 200) -> JsonResponse:
    return JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})


# ------------------------------------------------------------------ #
# health & search
# ------------------------------------------------------------------ #
def health(request):
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False

    return _ok(
        {
            "ok": True,
            "ytdlp": ytdlp.version(),
            "ffmpeg": bool(ytdlp.find_ffmpeg()),
            "database": db_ok,
            "downloadDir": str(storage.download_dir()),
            "active": sum(1 for j in jobs.list_jobs() if j["status"] in ("downloading", "converting")),
            "queued": sum(1 for j in jobs.list_jobs() if j["status"] == "queued"),
        }
    )


# ------------------------------------------------------------------ #
# pengaturan folder penyimpanan
# ------------------------------------------------------------------ #
def app_settings(request):
    if request.method == "GET":
        return _ok(storage.info())

    if request.method not in ("POST", "DELETE"):
        return HttpResponseNotAllowed(["GET", "POST", "DELETE"])

    try:
        if request.method == "DELETE":
            result = storage.reset_download_dir()
        else:
            body = _json_body(request)
            move_files = body.get("moveFiles", True) is not False
            if body.get("reset"):
                result = storage.reset_download_dir(move_files=move_files)
            else:
                result = storage.set_download_dir(body.get("downloadDir"), move_files=move_files)
        return _ok(result)
    except storage.StorageError as exc:
        return _error(str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        return _error(f"Gagal menyimpan folder: {exc}", 500)


@csrf_exempt
def settings_browse(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    return _ok(storage.browse_dir())


@csrf_exempt
def search(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        body = _json_body(request)
        results = ytdlp.search(body.get("query", ""), body.get("limit", settings.MAX_RESULTS))

        # tandai hasil yang MP3-nya sudah pernah dikonversi
        for item in results:
            path = jobs.mp3_path(item["id"])
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            if size > 1024:
                track = Track.objects.filter(video_id=item["id"]).first()
                item["cached"] = True
                item["size"] = size
                item["sizeLabel"] = jobs.human_size(size)
                item["fileName"] = track.file_name if track else f"{item['id']}.mp3"
            else:
                item["cached"] = False

        return _ok({"query": body.get("query", ""), "count": len(results), "results": results})
    except ValueError as exc:
        return _error(str(exc), 400)
    except subprocess.TimeoutExpired:
        return _error("Pencarian timeout. Coba lagi.", 504)
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc), 502)


# ------------------------------------------------------------------ #
# job konversi
# ------------------------------------------------------------------ #
@csrf_exempt
def convert(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        body = _json_body(request)
        job = jobs.create_job(body)
        return _ok(job, 202)
    except ValueError as exc:
        return _error(str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        return _error(f"Gagal memulai konversi: {exc}", 500)


@csrf_exempt
def job_detail(request, video_id: str):
    if not VIDEO_ID_RE.match(video_id):
        return _error("ID video tidak valid", 400)

    if request.method == "DELETE":
        job = jobs.cancel_job(video_id)
        return _ok(job or {"ok": True})

    if request.method != "GET":
        return HttpResponseNotAllowed(["GET", "DELETE"])

    job = jobs.get_job(video_id)
    if not job:
        return _error("Job tidak ditemukan", 404)
    return _ok(job)


def jobs_list(request):
    return _ok({"jobs": jobs.list_jobs()})


# ------------------------------------------------------------------ #
# library (riwayat dari PostgreSQL)
# ------------------------------------------------------------------ #
def library(request):
    if request.method == "GET":
        items = []
        for track in Track.objects.all()[:200]:
            path = jobs.mp3_path(track.video_id)
            if not path.exists() or path.stat().st_size < 1024:
                continue
            item = jobs.serialize_track(track)
            item["size"] = path.stat().st_size
            items.append(item)
        return _ok({"count": len(items), "items": items})

    return HttpResponseNotAllowed(["GET"])


@csrf_exempt
def library_item(request, video_id: str):
    if request.method != "DELETE":
        return HttpResponseNotAllowed(["DELETE"])
    if not VIDEO_ID_RE.match(video_id):
        return _error("ID tidak valid", 400)

    Track.objects.filter(video_id=video_id).delete()
    jobs.mp3_path(video_id).unlink(missing_ok=True)
    storage.sidecar_path(video_id).unlink(missing_ok=True)
    jobs.cancel_job(video_id)
    return _ok({"ok": True})


# ------------------------------------------------------------------ #
# streaming file mp3 (dukung Range agar bisa seek)
# ------------------------------------------------------------------ #
def _chunks(path: Path, start: int, end: int):
    with open(path, "rb") as handle:
        handle.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            data = handle.read(min(CHUNK, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data


def _range_header(value: str, size: int):
    match = re.match(r"^bytes=(\d*)-(\d*)$", value.strip())
    if not match:
        return None
    raw_start, raw_end = match.groups()
    if raw_start == "":
        suffix = int(raw_end or 0)
        if suffix <= 0:
            return None
        start = max(size - suffix, 0)
        end = size - 1
    else:
        start = int(raw_start)
        end = int(raw_end) if raw_end else size - 1
        end = min(end, size - 1)
    if start >= size or start > end:
        return None
    return start, end


def media(request, video_id: str):
    if not VIDEO_ID_RE.match(video_id):
        return _error("ID tidak valid", 400)
    if request.method not in ("GET", "HEAD"):
        return HttpResponseNotAllowed(["GET", "HEAD"])

    path = jobs.mp3_path(video_id)
    if not path.exists():
        return _error("File belum tersedia", 404)

    size = path.stat().st_size
    download = request.GET.get("download") == "1"

    track = Track.objects.filter(video_id=video_id).first()
    file_name = track.file_name if track else f"{video_id}.mp3"
    disposition = content_disposition_header(download, file_name)

    range_value = request.headers.get("Range")
    if range_value:
        parsed = _range_header(range_value, size)
        if not parsed:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
            return response
        start, end = parsed
        response = StreamingHttpResponse(
            _chunks(path, start, end),
            status=206,
            content_type="audio/mpeg",
        )
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
        response["Content-Length"] = str(end - start + 1)
    else:
        response = StreamingHttpResponse(_chunks(path, 0, size - 1), content_type="audio/mpeg")
        response["Content-Length"] = str(size)

    response["Accept-Ranges"] = "bytes"
    response["Cache-Control"] = "no-store"
    response["Content-Disposition"] = disposition
    return response


# ------------------------------------------------------------------ #
# stream langsung dari YouTube (tanpa menyimpan file)
# ------------------------------------------------------------------ #
STREAM_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def _open_stream(url: str, range_value: str | None):
    headers = {
        "User-Agent": STREAM_UA,
        "Accept": "*/*",
        "Accept-Encoding": "identity",
    }
    if range_value:
        headers["Range"] = range_value
    request = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(request, timeout=30)


def _resolve_with_retry(video_id: str, range_value: str | None):
    """Buka koneksi ke googlevideo; resolve ulang sekali kalau URL kedaluwarsa."""
    url = ytdlp.resolve_stream(video_id)
    try:
        return _open_stream(url, range_value)
    except urllib.error.HTTPError as exc:
        if exc.code not in (401, 403, 410):
            raise
        url = ytdlp.resolve_stream(video_id, force=True)
        return _open_stream(url, range_value)


def _stream_chunks(upstream):
    try:
        while True:
            data = upstream.read(CHUNK)
            if not data:
                break
            yield data
    finally:
        try:
            upstream.close()
        except Exception:  # noqa: BLE001
            pass


def stream(request, video_id: str):
    if not VIDEO_ID_RE.match(video_id):
        return _error("ID tidak valid", 400)
    if request.method not in ("GET", "HEAD"):
        return HttpResponseNotAllowed(["GET", "HEAD"])

    range_value = request.headers.get("Range")

    try:
        if request.method == "HEAD":
            upstream = _resolve_with_retry(video_id, "bytes=0-0")
            try:
                content_type = upstream.headers.get("Content-Type") or "audio/mp4"
                content_range = upstream.headers.get("Content-Range") or ""
            finally:
                upstream.close()

            response = HttpResponse(status=200)
            response["Content-Type"] = content_type
            response["Accept-Ranges"] = "bytes"
            response["Cache-Control"] = "no-store"
            if "/" in content_range:
                total = content_range.rsplit("/", 1)[-1]
                if total.isdigit():
                    response["Content-Length"] = total
            return response

        upstream = _resolve_with_retry(video_id, range_value)
        if upstream.status not in (200, 206):
            upstream.close()
            return _error(f"YouTube membalas HTTP {upstream.status}", 502)

        response = StreamingHttpResponse(
            _stream_chunks(upstream),
            status=upstream.status,
            content_type=upstream.headers.get("Content-Type") or "audio/mp4",
        )
        for header in ("Content-Length", "Content-Range"):
            value = upstream.headers.get(header)
            if value:
                response[header] = value
        response["Accept-Ranges"] = upstream.headers.get("Accept-Ranges") or "bytes"
        response["Cache-Control"] = "no-store"
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Expose-Headers"] = "Content-Length, Content-Range, Accept-Ranges"
        return response
    except ValueError as exc:
        return _error(str(exc), 400)
    except subprocess.TimeoutExpired:
        return _error("Resolve stream timeout. Coba lagi.", 504)
    except urllib.error.HTTPError as exc:
        return _error(f"YouTube menolak stream (HTTP {exc.code}). Coba lagi.", 502)
    except Exception as exc:  # noqa: BLE001
        return _error(f"Gagal stream: {exc}", 502)


# ------------------------------------------------------------------ #
# buka folder (Windows)
# ------------------------------------------------------------------ #
@csrf_exempt
def open_folder(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if os.name != "nt":
        return _ok({"ok": False, "message": "Hanya tersedia di Windows"})

    try:
        body = _json_body(request)
    except ValueError:
        body = {}

    video_id = str(body.get("id") or "").strip()
    if video_id:
        if not VIDEO_ID_RE.match(video_id):
            return _error("ID tidak valid", 400)
        path = jobs.mp3_path(video_id)
        if not path.exists():
            return _error("File belum ada", 404)
        subprocess.Popen(["explorer.exe", f"/select,{path}"])
    else:
        directory = storage.download_dir()
        subprocess.Popen(["explorer.exe", str(directory)])

    return _ok({"ok": True})


# ------------------------------------------------------------------ #
# serve React build (SPA)
# ------------------------------------------------------------------ #
DEV_PAGE = """<!doctype html><html lang="id"><head><meta charset="utf-8">
<title>ytmp3 — frontend belum di-build</title>
<style>
  body{background:#08080d;color:#f4f4f7;font-family:Segoe UI,system-ui,sans-serif;
       display:grid;place-items:center;min-height:100vh;margin:0;padding:24px}
  .card{max-width:560px;border:1px solid rgba(255,255,255,.12);border-radius:18px;
        padding:28px 30px;background:rgba(255,255,255,.04)}
  h1{font-size:20px;margin:0 0 12px}
  code{background:rgba(255,255,255,.08);padding:2px 7px;border-radius:6px}
  pre{background:rgba(255,255,255,.06);padding:14px;border-radius:10px;overflow:auto}
  a{color:#c084fc}
</style></head><body><div class="card">
<h1>Frontend belum di-build</h1>
<p>API Django sudah jalan. Untuk mode development jalankan frontend Vite:</p>
<pre>cd frontend
pnpm install
pnpm dev</pre>
<p>Lalu buka <a href="http://localhost:5233">http://localhost:5233</a>.</p>
<p>Atau build untuk produksi:</p>
<pre>cd frontend
pnpm build</pre>
<p>Setelah build, halaman ini otomatis menampilkan aplikasi React.</p>
</div></body></html>"""


def spa(request, path: str = ""):
    dist = Path(settings.FRONTEND_DIST)
    index = dist / "index.html"

    if not index.exists():
        return HttpResponse(DEV_PAGE, content_type="text/html; charset=utf-8")

    target = (dist / path).resolve()
    try:
        target.relative_to(dist.resolve())
    except ValueError:
        raise Http404("Not found") from None

    if target.is_dir():
        target = target / "index.html"
    if not target.exists():
        target = index

    content_type, _ = mimetypes.guess_type(str(target))
    response = FileResponse(open(target, "rb"), content_type=content_type or "application/octet-stream")
    if "/assets/" in str(target):
        response["Cache-Control"] = "public, max-age=31536000, immutable"
    return response
