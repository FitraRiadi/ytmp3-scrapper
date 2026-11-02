"""Preferensi penyimpanan: folder MP3 custom + pemindahan file lama."""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings


class StorageError(ValueError):
    """Path folder tidak valid / tidak bisa dipakai."""


_lock = threading.RLock()
_dialog_busy = threading.Lock()
_cached: Path | None = None


# ------------------------------------------------------------------ #
# preferensi
# ------------------------------------------------------------------ #
def default_dir() -> Path:
    return Path(settings.DOWNLOAD_DIR)


def _prefs_file() -> Path:
    return Path(settings.PREFERENCES_FILE)


def _read_prefs() -> dict:
    try:
        data = json.loads(_prefs_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_prefs(data: dict) -> None:
    target = _prefs_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, target)


def download_dir(create: bool = True) -> Path:
    """Folder aktif. Selalu dibuat bila belum ada."""
    global _cached
    with _lock:
        if _cached is None:
            raw = str(_read_prefs().get("downloadDir") or "").strip()
            if raw:
                try:
                    _cached = Path(os.path.expandvars(raw)).expanduser()
                except (OSError, ValueError):
                    _cached = default_dir()
            else:
                _cached = default_dir()

        path = _cached or default_dir()
        if create:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError:
                path = default_dir()
                path.mkdir(parents=True, exist_ok=True)
                _cached = path
        return path


def _same_path(first: Path, second: Path) -> bool:
    try:
        return os.path.normcase(str(first.resolve(strict=False))) == os.path.normcase(
            str(second.resolve(strict=False))
        )
    except OSError:
        return os.path.normcase(str(first)) == os.path.normcase(str(second))


def _normalize(raw: object) -> Path:
    text = str(raw or "").strip().strip('"').strip("'")
    if not text:
        raise StorageError("Path folder tidak boleh kosong")
    expanded = os.path.expandvars(os.path.expanduser(text))
    path = Path(expanded)
    if not path.is_absolute():
        raise StorageError("Gunakan path absolut, misalnya D:\\Music\\ytmp3")
    if path.exists() and not path.is_dir():
        raise StorageError("Path tersebut adalah file, bukan folder")
    return path


def _probe_writable(path: Path) -> bool:
    probe = path / f".ytmp3-write-test-{os.getpid()}-{time.time_ns()}"
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe.write_bytes(b"ok")
        probe.unlink()
        return True
    except OSError:
        return False


def _count_files(path: Path) -> int:
    try:
        return sum(1 for item in path.glob("*.mp3") if item.stat().st_size > 1024)
    except OSError:
        return 0


# ------------------------------------------------------------------ #
# sidecar metadata (<videoId>.json)
# ------------------------------------------------------------------ #
def sidecar_path(video_id: str, directory: Path | None = None) -> Path:
    return (directory or download_dir()) / f"{video_id}.json"


def write_sidecar(
    record: dict,
    created_at: str | None = None,
    directory: Path | None = None,
) -> Path:
    """Tulis metadata yang bisa dibaca tanpa database/API."""
    video_id = str(record["id"])
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "id": video_id,
        "title": record.get("title", ""),
        "channel": record.get("channel", ""),
        "duration": int(record.get("duration") or 0),
        "thumbnail": record.get("thumbnail", ""),
        "file": f"{video_id}.mp3",
        "fileName": record.get("file_name") or record.get("fileName") or f"{video_id}.mp3",
        "size": int(record.get("size") or 0),
        "sourceUrl": f"https://www.youtube.com/watch?v={video_id}",
        "createdAt": created_at or now,
        "updatedAt": now,
    }
    target = sidecar_path(video_id, directory)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    return target


def read_sidecar(video_id: str) -> dict:
    try:
        data = json.loads(sidecar_path(video_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def info() -> dict:
    current = download_dir()
    default = default_dir()
    return {
        "downloadDir": str(current),
        "defaultDir": str(default),
        "isDefault": _same_path(current, default),
        "exists": current.exists(),
        "writable": _probe_writable(current),
        "files": _count_files(current),
    }


def _move_mp3(old: Path, new: Path) -> tuple[int, int, list[str]]:
    """Pindahkan MP3 final dari folder lama ke folder baru."""
    moved = 0
    skipped = 0
    errors: list[str] = []
    if _same_path(old, new) or not old.exists():
        return moved, skipped, errors

    try:
        candidates = sorted(old.glob("*.mp3"))
    except OSError as exc:
        return moved, skipped, [f"{old}: {exc}"]

    for source in candidates:
        try:
            if source.stat().st_size < 1024:
                continue
            target = new / source.name
            if target.exists():
                skipped += 1
                continue
            shutil.move(str(source), str(target))

            sidecar = source.with_suffix(".json")
            if sidecar.exists():
                side_target = new / sidecar.name
                if not side_target.exists():
                    shutil.move(str(sidecar), str(side_target))

            moved += 1
        except OSError as exc:
            errors.append(f"{source.name}: {exc}")
    return moved, skipped, errors


def set_download_dir(raw: object, move_files: bool = True) -> dict:
    """Ganti folder aktif, opsional pindahkan MP3 yang sudah ada."""
    global _cached
    with _lock:
        path = _normalize(raw)
        old = download_dir()

        if not _probe_writable(path):
            raise StorageError(f"Folder tidak bisa ditulis: {path}")

        moved, skipped, errors = (0, 0, [])
        if not _same_path(old, path):
            if move_files:
                moved, skipped, errors = _move_mp3(old, path)
            _write_prefs({**_read_prefs(), "downloadDir": str(path)})

        _cached = path
        return {**info(), "moved": moved, "skipped": skipped, "moveErrors": errors}


def reset_download_dir(move_files: bool = True) -> dict:
    """Kembali ke folder default."""
    global _cached
    with _lock:
        old = download_dir()
        default = default_dir()
        default.mkdir(parents=True, exist_ok=True)

        moved, skipped, errors = (0, 0, [])
        if not _same_path(old, default) and move_files:
            moved, skipped, errors = _move_mp3(old, default)

        prefs = _read_prefs()
        prefs.pop("downloadDir", None)
        _write_prefs(prefs)
        _cached = default
        return {**info(), "moved": moved, "skipped": skipped, "moveErrors": errors}


# ------------------------------------------------------------------ #
# dialog pilih folder (Windows)
# ------------------------------------------------------------------ #
def browse_dir() -> dict:
    """Buka dialog folder native lewat tkinter (dipanggil dari server lokal)."""
    if os.name != "nt":
        return {"ok": False, "message": "Pemilih folder hanya tersedia di Windows"}
    if not _dialog_busy.acquire(blocking=False):
        return {"ok": False, "message": "Dialog folder sedang terbuka"}

    root = None
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.update_idletasks()

        selected = filedialog.askdirectory(
            parent=root,
            title="Pilih folder penyimpanan MP3",
            initialdir=str(download_dir()),
            mustexist=False,
        )
        if not selected:
            return {"ok": False, "canceled": True, "message": "Tidak ada folder dipilih"}
        return {"ok": True, "path": str(Path(selected))}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Dialog tidak tersedia: {exc}"}
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:  # noqa: BLE001
                pass
        _dialog_busy.release()
