# ytmp3-scrapper

Search for a song on YouTube, convert it to MP3, preview it in the browser, and download it —
all from a single page. Built with Django + React, powered by `yt-dlp` and `ffmpeg`, with
PostgreSQL for storing your collection.

> This project is intended for personal/local use. Only download content you have the right to
> access, and respect copyright as well as YouTube's Terms of Service.

---

## Features

- **Search without an API key** — uses `yt-dlp "ytsearch5:<query>"`; you can also paste a
  YouTube URL directly.
- **Up to 5 results** — title, channel, duration, view count, and thumbnail.
- **MP3 conversion** — highest VBR quality (`--audio-quality 0`) with embedded ID3 metadata.
- **Two-worker queue** — at most two conversions run at once; the rest wait in the queue.
- **Real-time progress** — `queued → downloading → converting → ready` (or `error`).
- **Cancel a conversion** — stops the `yt-dlp`/`ffmpeg` process and removes partial files.
- **Streaming preview** — supports HTTP Range requests, so you can seek through the audio.
- **Clean downloads** — files are named `Channel - Title.mp3`.
- **Automatic cache** — songs whose MP3 already exists are immediately ready.
- **Custom download folder** — choose your own folder from the settings dialog; existing files
  can be moved along with it.
- **Sidecar metadata** — every MP3 gets a matching `.json` file containing the title, channel,
  duration, and source URL, so song names stay readable without opening the database.
- **Library** — history is stored in PostgreSQL and can be played, downloaded, or deleted.

---

## Stack

| Part     | Technology                                                              |
| -------- | ----------------------------------------------------------------------- |
| Frontend | React 19, Vite 8, Tailwind CSS 4, shadcn/ui, axios, lucide-react, sonner |
| Backend  | Python 3.11+, Django 5.2                                                |
| Database | PostgreSQL (`psycopg` 3 driver)                                         |
| Engine   | `yt-dlp` (auto-downloaded into `bin/`) + `ffmpeg`                       |
| Tooling  | `pnpm` for the frontend, `pip` for the backend                          |

---

## Project structure

```text
ytmp3-scrapper/
├─ backend/
│  ├─ manage.py
│  ├─ requirements.txt
│  ├─ .env.example
│  ├─ config/               # settings, URLs, WSGI/ASGI
│  └─ api/                  # views, jobs, storage, ytdlp, models, migrations
├─ frontend/
│  ├─ package.json
│  ├─ vite.config.js        # port 5233, /api proxy -> 8137
│  └─ src/                  # App, components, lib/api.js
├─ bin/                     # yt-dlp (auto-downloaded, not committed)
├─ downloads/               # MP3 + sidecar .json (not committed)
├─ dev.ps1                  # run backend + frontend (Windows)
└─ README.md
```

---

## Requirements

- **Python 3.11+** and `pip`
- **Node.js 20+** and **pnpm**
- **PostgreSQL** running (default `127.0.0.1:5432`)
- **ffmpeg** available in `PATH`
  - Windows: `winget install Gyan.FFmpeg`
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

You do not need to install `yt-dlp` manually. On first run, the app downloads the appropriate
binary into the `bin/` folder.

Quick check:

```powershell
py --version
node --version
pnpm --version
ffmpeg -version
```

---

## Installation

### 1. Clone the repository

```powershell
git clone https://github.com/FitraRiadi/ytmp3-scrapper.git
cd ytmp3-scrapper
```

### 2. Create the database

Create an empty database (example using `psql`):

```powershell
psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE ytmp3_scrapper ENCODING 'UTF8'"
```

Adjust the database name or user if needed.

### 3. Backend

```powershell
cd backend
copy .env.example .env
```

Open `backend/.env` and fill in `DB_PASSWORD` (and any other values as needed). Then:

```powershell
py -m pip install -r requirements.txt
py manage.py migrate
py manage.py runserver 127.0.0.1:8137
```

Check: <http://127.0.0.1:8137/api/health>

```json
{
  "ok": true,
  "ytdlp": "2026.10.26",
  "ffmpeg": true,
  "database": true,
  "downloadDir": "D:\\path\\to\\ytmp3-scrapper\\downloads",
  "active": 0,
  "queued": 0
}
```

### 4. Frontend (development)

In another terminal:

```powershell
cd frontend
pnpm install
pnpm dev
```

Open <http://localhost:5233>. Vite proxies `/api` to Django on `8137`, so there are no CORS
issues.

### 5. Production build

```powershell
cd frontend
pnpm build
```

The build output goes to `frontend/dist`. Django can then serve the app and the API together:

```powershell
cd backend
py manage.py runserver 127.0.0.1:8137
```

Open <http://127.0.0.1:8137>.

### Shortcut (Windows)

```powershell
.\dev.ps1
```

This opens two windows: Django on `8137` and Vite on `5233`.

---

## Usage

1. Enter a song title or paste a YouTube URL, then press **Search**.
2. Pick one of the up to 5 results.
3. Click **Convert** and wait for the status to become **Ready**.
4. Click **Preview** to play it (seeking is supported) or **Download** to save the MP3.
5. Finished songs automatically appear in your **Library**.
6. Click the **gear** icon in the header to change the download folder.

Download folder behavior:

- The path must be absolute, e.g. `D:\Music\ytmp3`.
- The folder is created automatically if it does not exist.
- **Move existing MP3s** moves already-downloaded files into the new folder.
- The **Default** button switches back to the in-project `downloads/` folder.
- Conversions already in progress finish in their original folder.

---

## Configuration

### Backend environment

Values are read from `backend/.env` (or `.env` in the project root). Existing environment
variables take precedence.

| Variable            | Default                        | Description                         |
| ------------------- | ------------------------------ | ----------------------------------- |
| `DJANGO_DEBUG`      | `1`                            | Set to `0` for production           |
| `DJANGO_SECRET_KEY` | `dev-only-...`                 | Replace with a random string        |
| `DB_NAME`           | `ytmp3_scrapper`               | Database name                       |
| `DB_USER`           | `postgres`                     | Database user                       |
| `DB_PASSWORD`       | *(empty)*                      | Database password                   |
| `DB_HOST`           | `127.0.0.1`                    | Database host                       |
| `DB_PORT`           | `5432`                         | Database port                       |
| `DOWNLOAD_DIR`      | `<root>/downloads`             | Default download folder             |

### Application constants

Defined in `backend/config/settings.py`:

| Constant              | Default                        | Purpose                             |
| --------------------- | ------------------------------ | ----------------------------------- |
| `MAX_RESULTS`         | `5`                            | Search result limit                 |
| `MAX_CONCURRENT_JOBS` | `2`                            | Parallel conversions                |
| `BIN_DIR`             | `<root>/bin`                   | Location of the `yt-dlp` binary     |
| `FRONTEND_DIST`       | `<root>/frontend/dist`         | Build output served by Django       |
| `PREFERENCES_FILE`    | `<root>/data/preferences.json` | Custom download folder preferences  |

### Ports

| Service    | Port | Configured in                          |
| ---------- | ---- | -------------------------------------- |
| Django API | 8137 | `runserver` command / `dev.ps1`        |
| Vite dev   | 5233 | `frontend/vite.config.js`              |

If you change a port, update the `/api` proxy target in `vite.config.js` as well.

---

## API

Development base URL: `http://127.0.0.1:8137/api` (or via Vite at `http://localhost:5233/api`).

- Format: JSON, except for media endpoints (`audio/mpeg`) and SPA pages.
- Errors: `{ "error": "message" }`.
- There is no authentication and CSRF is disabled. Run this only in a trusted environment.

| Method    | Endpoint                | Description                            |
| --------- | ----------------------- | -------------------------------------- |
| GET       | `/api/health`           | Engine, database, and folder status    |
| POST      | `/api/search`           | Search videos (max 5)                  |
| POST      | `/api/convert`          | Start an MP3 conversion                |
| GET       | `/api/jobs`             | All in-memory jobs                     |
| GET       | `/api/job/<id>`         | Status of a single job                 |
| DELETE    | `/api/job/<id>`         | Cancel a job                           |
| GET       | `/api/library`          | Collection from the database           |
| DELETE    | `/api/library/<id>`     | Delete song + MP3 + sidecar            |
| GET/HEAD  | `/api/media/<id>`       | Stream MP3 (Range) / download          |
| POST      | `/api/open-folder`      | Open Explorer (Windows)                |
| GET       | `/api/settings`         | Download folder info                   |
| POST      | `/api/settings`         | Change folder / reset                  |
| DELETE    | `/api/settings`         | Reset to the default folder            |
| POST      | `/api/settings/browse`  | Native folder picker (Windows)         |
| GET       | `/*` (outside `/api/`)  | React app / build assets               |

### `POST /api/search`

```json
{ "query": "NIKI - lowkey", "limit": 5 }
```

Response:

```json
{
  "query": "NIKI - lowkey",
  "count": 1,
  "results": [
    {
      "id": "9jz3fWYwMuc",
      "title": "lowkey",
      "channel": "NIKI",
      "channelVerified": true,
      "duration": 172,
      "viewCount": 12345678,
      "thumbnail": "https://i.ytimg.com/vi/9jz3fWYwMuc/mqdefault.jpg",
      "url": "https://www.youtube.com/watch?v=9jz3fWYwMuc",
      "live": false,
      "cached": true,
      "size": 5517032,
      "sizeLabel": "5.3 MB",
      "fileName": "NIKI - lowkey.mp3"
    }
  ]
}
```

The `size`, `sizeLabel`, and `fileName` fields only appear when `cached` is `true`.

### `POST /api/convert`

```json
{
  "id": "9jz3fWYwMuc",
  "title": "lowkey",
  "channel": "NIKI",
  "duration": 172,
  "thumbnail": "https://i.ytimg.com/vi/9jz3fWYwMuc/mqdefault.jpg"
}
```

Jobs are idempotent per video ID. If the file already exists, the response is immediately
`ready` with `cached: true`. Otherwise, the job is queued.

Example job object:

```json
{
  "id": "9jz3fWYwMuc",
  "title": "lowkey",
  "channel": "NIKI",
  "duration": 172,
  "thumbnail": "https://i.ytimg.com/vi/9jz3fWYwMuc/mqdefault.jpg",
  "status": "downloading",
  "progress": 42,
  "message": "Downloading audio... 49.4%",
  "size": 0,
  "sizeLabel": null,
  "fileName": "NIKI - lowkey.mp3",
  "error": null,
  "cached": false,
  "mediaUrl": null,
  "downloadUrl": null
}
```

Statuses: `queued`, `downloading`, `converting`, `ready`, `error`.
When `ready`, `mediaUrl` and `downloadUrl` are populated.

### `GET /api/library`

```json
{
  "count": 1,
  "items": [
    {
      "id": "9jz3fWYwMuc",
      "title": "lowkey",
      "channel": "NIKI",
      "duration": 172,
      "status": "ready",
      "progress": 100,
      "size": 5517032,
      "sizeLabel": "5.3 MB",
      "fileName": "NIKI - lowkey.mp3",
      "mediaUrl": "/api/media/9jz3fWYwMuc",
      "downloadUrl": "/api/media/9jz3fWYwMuc?download=1",
      "createdAt": "2026-11-02T14:53:14+00:00"
    }
  ]
}
```

Only songs whose files still exist in the active folder are listed.

### Streaming & download

```text
GET /api/media/<id>              -> play in the browser
GET /api/media/<id>?download=1   -> Content-Disposition: attachment
```

Supports `Range` requests (`206` responses) for seeking. `HEAD` is supported as well.

### Folder settings

```text
GET    /api/settings
POST   /api/settings              { "downloadDir": "D:\\Music\\ytmp3", "moveFiles": true }
POST   /api/settings              { "reset": true }
DELETE /api/settings
POST   /api/settings/browse       opens a native folder picker (Windows)
```

The response includes `downloadDir`, `defaultDir`, `isDefault`, `exists`, `writable`, and
`files`. When changing folders it also returns `moved`, `skipped`, and `moveErrors`.

### Open folder

```text
POST /api/open-folder  { "id": "9jz3fWYwMuc" }  -> select the file in Explorer
POST /api/open-folder  {}                        -> open the active download folder
```

Windows only; on other platforms the response is `{ "ok": false, "message": "..." }`.

---

## File storage

MP3 files are stored under their video ID, which keeps names unique and easy to check:

```text
downloads/
├─ 9jz3fWYwMuc.mp3
├─ 9jz3fWYwMuc.json     # sidecar metadata
├─ OqBuXQLR4Y8.mp3
└─ OqBuXQLR4Y8.json
```

The filename users receive is still clean (`Channel - Title.mp3`) thanks to the
`Content-Disposition` header. Metadata is also embedded in the MP3 (ID3 tags).

Sidecar example:

```json
{
  "id": "9jz3fWYwMuc",
  "title": "lowkey",
  "channel": "NIKI",
  "duration": 172,
  "thumbnail": "https://i.ytimg.com/vi/9jz3fWYwMuc/mqdefault.jpg",
  "file": "9jz3fWYwMuc.mp3",
  "fileName": "NIKI - lowkey.mp3",
  "size": 5517032,
  "sourceUrl": "https://www.youtube.com/watch?v=9jz3fWYwMuc",
  "createdAt": "2026-11-02T14:53:14+00:00",
  "updatedAt": "2026-11-02T15:59:33+00:00"
}
```

If a sidecar is missing (for example, for older files), regenerate them with:

```powershell
cd backend
py manage.py sync_sidecars
```

The database stores an `api_track` table:

| Column       | Content                          |
| ------------ | -------------------------------- |
| `video_id`   | YouTube ID (unique)              |
| `title`      | Song title                       |
| `channel`    | Channel/artist                   |
| `duration`   | Duration in seconds              |
| `thumbnail`  | Thumbnail URL                    |
| `file_name`  | Download filename                |
| `file_size`  | Size in bytes                    |
| `created_at` | Creation timestamp               |
| `updated_at` | Last update timestamp            |

No absolute paths are stored in the database; files are always looked up in the active folder.

---

## How it works

**Search**

```text
yt-dlp "ytsearch5:<query>" --flat-playlist --dump-json --no-warnings --ignore-errors
```

**Conversion**

```text
yt-dlp -f bestaudio/best -x --audio-format mp3 --audio-quality 0 --embed-metadata
       --no-playlist --newline -o <folder>/<id>.%(ext)s https://www.youtube.com/watch?v=<id>
```

- Conversions run in a thread pool inside the Django process (up to two workers).
- Download progress maps to 0–85, the conversion stage to 88, and completion to 100.
- Jobs live in memory; final results are written to PostgreSQL and a `.json` sidecar.
- The frontend polls `GET /api/job/<id>` while any job is active.

---

## Troubleshooting

| Problem                             | Solution                                                                    |
| ----------------------------------- | --------------------------------------------------------------------------- |
| `ffmpeg` not detected               | Install ffmpeg, make sure it is on `PATH`, then restart the backend.         |
| Search fails / bot check            | Update yt-dlp (`py manage.py update_ytdlp`) and try again later.             |
| Conversion error "Sign in to confirm" | The video requires login/age verification, or YouTube blocked the IP.      |
| `database down` in the header       | Check PostgreSQL, the database name, and your `.env` file.                  |
| Blank frontend on port 8137         | Run `pnpm build` in the `frontend` folder.                                  |
| Port already in use                 | Stop the other process or change the Django port and Vite proxy.            |
| Preview cannot seek                 | Make sure the media endpoint returns `206` and `Accept-Ranges: bytes`.      |
| Folder is not writable              | Use an absolute path the user can access, or choose another folder.         |
| Folder picker does not appear       | Windows and an interactive desktop are required; enter the path manually.  |
| Song names are not visible in the folder | Read the `<videoId>.json` sidecar or the MP3 ID3 tags.                  |

Check the backend:

```powershell
curl.exe http://127.0.0.1:8137/api/health
```

Update the engine:

```powershell
cd backend
py manage.py update_ytdlp
```

---

## Limitations & security

- **No authentication** — this app is designed for local use. Do not expose it directly to the
  internet without additional protection.
- **In-memory jobs** — progress is lost when the backend restarts; files and the library remain.
- **Not built for multi-instance/serverless** — workers run inside the Django process.
- **No rate limiting** — avoid excessive requests.
- **Windows-specific features** — opening folders and the folder picker rely on Explorer/tkinter.
- **Audio only** — no video and no playlists.
- **Files are not deleted automatically** — manage them with the delete button in the library.
- **Copyright** — only use content you have the right to download; respect YouTube's ToS.

---

## Contributing

Pull requests and issues are welcome. For larger changes, please open an issue first so the
approach can be discussed.
