# ytmp3-scrapper

Cari lagu di YouTube, ubah jadi MP3, putar preview di browser, lalu download — semuanya dari
satu halaman. Dibangun dengan Django + React, memakai `yt-dlp` dan `ffmpeg`, serta PostgreSQL
untuk menyimpan koleksi.

> Proyek ini untuk pemakaian pribadi/lokal. Gunakan hanya untuk konten yang kamu berhak
> mengunduhnya dan hormati hak cipta serta Ketentuan Layanan YouTube.

---

## Fitur

- **Cari tanpa API key** — memakai `yt-dlp "ytsearch5:<query>"`, bisa juga menempel URL YouTube.
- **Maksimal 5 hasil** — judul, channel, durasi, jumlah view, dan thumbnail.
- **Convert ke MP3** — kualitas VBR tertinggi (`--audio-quality 0`) + metadata ID3.
- **Antrian 2 worker** — maksimal 2 konversi berjalan bersamaan, sisanya menunggu.
- **Progress realtime** — `queued → downloading → converting → ready` (atau `error`).
- **Batalkan konversi** — proses `yt-dlp`/`ffmpeg` dihentikan, file setengah jadi dibersihkan.
- **Preview streaming** — mendukung HTTP Range, jadi audio bisa di-seek.
- **Download rapi** — nama file `Channel - Title.mp3`.
- **Cache otomatis** — video yang MP3-nya sudah ada langsung siap dipakai.
- **Folder penyimpanan custom** — pilih folder sendiri lewat menu pengaturan; file lama bisa
  ikut dipindah.
- **Sidecar metadata** — setiap MP3 punya file `.json` berisi judul, channel, durasi, dan URL
  sumber, sehingga nama lagu tetap terbaca tanpa membuka database.
- **Koleksi** — riwayat tersimpan di PostgreSQL, bisa diputar, diunduh, atau dihapus.

---

## Stack

| Bagian   | Teknologi                                                              |
| -------- | ---------------------------------------------------------------------- |
| Frontend | React 19, Vite 8, Tailwind CSS 4, shadcn/ui, axios, lucide-react, sonner |
| Backend  | Python 3.11+, Django 5.2                                               |
| Database | PostgreSQL (driver `psycopg` 3)                                        |
| Engine   | `yt-dlp` (binary otomatis di `bin/`) + `ffmpeg`                        |
| Tooling  | `pnpm` untuk frontend, `pip` untuk backend                             |

---

## Struktur proyek

```text
ytmp3-scrapper/
├─ backend/
│  ├─ manage.py
│  ├─ requirements.txt
│  ├─ .env.example
│  ├─ config/               # settings, URL, WSGI/ASGI
│  └─ api/                  # views, jobs, storage, ytdlp, model, migrations
├─ frontend/
│  ├─ package.json
│  ├─ vite.config.js        # port 5233, proxy /api -> 8137
│  └─ src/                  # App, komponen, lib/api.js
├─ bin/                     # yt-dlp (diunduh otomatis, tidak di-commit)
├─ downloads/               # MP3 + sidecar .json (tidak di-commit)
├─ dev.ps1                  # jalankan backend + frontend (Windows)
└─ README.md
```

---

## Prasyarat

- **Python 3.11+** dan `pip`
- **Node.js 20+** dan **pnpm**
- **PostgreSQL** yang berjalan (default `127.0.0.1:5432`)
- **ffmpeg** tersedia di `PATH`
  - Windows: `winget install Gyan.FFmpeg`
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

`yt-dlp` tidak perlu dipasang manual. Saat pertama kali dijalankan, aplikasi mengunduh binary
yang sesuai ke folder `bin/`.

Cek cepat:

```powershell
py --version
node --version
pnpm --version
ffmpeg -version
```

---

## Instalasi

### 1. Clone & masuk ke folder

```powershell
git clone https://github.com/FitraRiadi/ytmp3-scrapper.git
cd ytmp3-scrapper
```

### 2. Siapkan database

Buat database kosong (contoh memakai `psql`):

```powershell
psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE ytmp3_scrapper ENCODING 'UTF8'"
```

Sesuaikan nama database/user kalau berbeda.

### 3. Backend

```powershell
cd backend
copy .env.example .env
```

Buka `backend/.env`, lalu isi `DB_PASSWORD` (dan variabel lain bila perlu). Setelah itu:

```powershell
py -m pip install -r requirements.txt
py manage.py migrate
py manage.py runserver 127.0.0.1:8137
```

Cek: <http://127.0.0.1:8137/api/health>

```json
{
  "ok": true,
  "ytdlp": "2026.10.26",
  "ffmpeg": true,
  "database": true,
  "downloadDir": "D:\\path\\ke\\ytmp3-scrapper\\downloads",
  "active": 0,
  "queued": 0
}
```

### 4. Frontend (development)

Buka terminal lain:

```powershell
cd frontend
pnpm install
pnpm dev
```

Buka <http://localhost:5233>. Vite mem-proxy `/api` ke Django di `8137`, jadi tidak ada
masalah CORS.

### 5. Build produksi

```powershell
cd frontend
pnpm build
```

Hasil build ada di `frontend/dist`. Setelah itu Django bisa menyajikan aplikasi sekaligus:

```powershell
cd backend
py manage.py runserver 127.0.0.1:8137
```

Buka <http://127.0.0.1:8137>.

### Shortcut (Windows)

```powershell
.\dev.ps1
```

Script ini membuka dua jendela: Django `8137` dan Vite `5233`.

---

## Cara pakai

1. Tulis judul lagu atau tempel URL YouTube, lalu tekan **Cari**.
2. Pilih salah satu dari maksimal 5 hasil.
3. Klik **Convert** dan tunggu sampai status **Siap**.
4. Klik **Preview** untuk memutar (bisa di-seek), atau **Download** untuk menyimpan MP3.
5. Lagu yang selesai otomatis masuk ke **Koleksi kamu**.
6. Klik ikon **gear** di header untuk mengganti folder penyimpanan.

Folder penyimpanan:

- Path harus absolut, mis. `D:\Music\ytmp3`.
- Folder dibuat otomatis kalau belum ada.
- Opsi **Pindahkan MP3 lama** memindahkan file yang sudah ada ke folder baru.
- Tombol **Default** mengembalikan ke folder `downloads/` di dalam proyek.
- Konversi yang sedang berjalan tetap diselesaikan di folder lamanya.

---

## Konfigurasi

### Environment backend

Dibaca dari `backend/.env` (atau `.env` di root proyek). Variabel environment yang sudah ada
akan menang.

| Variabel            | Default                        | Keterangan                          |
| ------------------- | ------------------------------ | ----------------------------------- |
| `DJANGO_DEBUG`      | `1`                            | `0` untuk produksi                  |
| `DJANGO_SECRET_KEY` | `dev-only-...`                 | ganti dengan string acak            |
| `DB_NAME`           | `ytmp3_scrapper`               | nama database                       |
| `DB_USER`           | `postgres`                     | user database                       |
| `DB_PASSWORD`       | *(kosong)*                     | password database                   |
| `DB_HOST`           | `127.0.0.1`                    | host database                       |
| `DB_PORT`           | `5432`                         | port database                       |
| `DOWNLOAD_DIR`      | `<root>/downloads`             | folder simpan default               |

### Konstanta aplikasi

Ada di `backend/config/settings.py`:

| Konstanta             | Default                     | Fungsi                              |
| --------------------- | --------------------------- | ----------------------------------- |
| `MAX_RESULTS`         | `5`                         | batas hasil pencarian               |
| `MAX_CONCURRENT_JOBS` | `2`                         | konversi paralel                    |
| `BIN_DIR`             | `<root>/bin`                | lokasi binary `yt-dlp`              |
| `FRONTEND_DIST`       | `<root>/frontend/dist`      | hasil build yang disajikan Django   |
| `PREFERENCES_FILE`    | `<root>/data/preferences.json` | preferensi folder simpan         |

### Port

| Service    | Port | Diatur di                              |
| ---------- | ---- | -------------------------------------- |
| Django API | 8137 | perintah `runserver` / `dev.ps1`       |
| Vite dev   | 5233 | `frontend/vite.config.js`              |

Kalau port diubah, sesuaikan juga target proxy `/api` di `vite.config.js`.

---

## API

Base URL development: `http://127.0.0.1:8137/api` (atau lewat Vite `http://localhost:5233/api`).

- Format: JSON, kecuali endpoint media (`audio/mpeg`) dan halaman SPA.
- Error: `{ "error": "pesan" }`.
- Tidak ada autentikasi dan CSRF dimatikan. Jalankan hanya di lingkungan tepercaya.

| Method    | Endpoint                | Fungsi                                |
| --------- | ----------------------- | ------------------------------------- |
| GET       | `/api/health`           | status engine, database, folder aktif |
| POST      | `/api/search`           | cari video (maks 5)                   |
| POST      | `/api/convert`          | mulai konversi MP3                    |
| GET       | `/api/jobs`             | semua job di memori                   |
| GET       | `/api/job/<id>`         | status satu job                       |
| DELETE    | `/api/job/<id>`         | batalkan job                          |
| GET       | `/api/library`          | koleksi dari database                 |
| DELETE    | `/api/library/<id>`     | hapus lagu + MP3 + sidecar            |
| GET/HEAD  | `/api/media/<id>`       | stream MP3 (Range) / download         |
| POST      | `/api/open-folder`      | buka Explorer (Windows)               |
| GET       | `/api/settings`         | info folder penyimpanan               |
| POST      | `/api/settings`         | ubah folder / reset                   |
| DELETE    | `/api/settings`         | reset ke folder default               |
| POST      | `/api/settings/browse`  | dialog pilih folder (Windows)         |
| GET       | `/*` (selain `/api/`)   | aplikasi React / aset build           |

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

Field `size`, `sizeLabel`, dan `fileName` hanya muncul kalau `cached: true`.

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

Job idempoten per video ID. Kalau file sudah ada, response langsung `ready` dengan
`cached: true`. Kalau belum, job masuk antrian.

Contoh job object:

```json
{
  "id": "9jz3fWYwMuc",
  "title": "lowkey",
  "channel": "NIKI",
  "duration": 172,
  "thumbnail": "https://i.ytimg.com/vi/9jz3fWYwMuc/mqdefault.jpg",
  "status": "downloading",
  "progress": 42,
  "message": "Mengunduh audio... 49.4%",
  "size": 0,
  "sizeLabel": null,
  "fileName": "NIKI - lowkey.mp3",
  "error": null,
  "cached": false,
  "mediaUrl": null,
  "downloadUrl": null
}
```

Status: `queued`, `downloading`, `converting`, `ready`, `error`.
Saat `ready`, `mediaUrl` dan `downloadUrl` terisi.

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

Hanya lagu yang filenya masih ada di folder aktif yang ditampilkan.

### Streaming & download

```text
GET /api/media/<id>              -> diputar di browser
GET /api/media/<id>?download=1   -> Content-Disposition: attachment
```

Mendukung `Range` (response `206`) supaya bisa di-seek. `HEAD` juga didukung.

### Pengaturan folder

```text
GET    /api/settings
POST   /api/settings              { "downloadDir": "D:\\Music\\ytmp3", "moveFiles": true }
POST   /api/settings              { "reset": true }
DELETE /api/settings
POST   /api/settings/browse       membuka dialog folder native (Windows)
```

Response berisi `downloadDir`, `defaultDir`, `isDefault`, `exists`, `writable`, `files`, dan
saat mengganti folder juga `moved`, `skipped`, `moveErrors`.

### Buka folder

```text
POST /api/open-folder  { "id": "9jz3fWYwMuc" }  -> pilih file di Explorer
POST /api/open-folder  {}                        -> buka folder simpan aktif
```

Khusus Windows; di OS lain response `{ "ok": false, "message": "..." }`.

---

## Penyimpanan file

MP3 disimpan dengan nama video ID agar unik dan mudah dicek:

```text
downloads/
├─ 9jz3fWYwMuc.mp3
├─ 9jz3fWYwMuc.json     # sidecar metadata
├─ OqBuXQLR4Y8.mp3
└─ OqBuXQLR4Y8.json
```

Nama file yang diunduh user tetap rapi (`Channel - Title.mp3`) lewat header
`Content-Disposition`. Metadata juga tertanam di MP3 (ID3).

Contoh sidecar:

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

Kalau sidecar hilang (misalnya file lama), buat ulang dengan:

```powershell
cd backend
py manage.py sync_sidecars
```

Database menyimpan tabel `api_track`:

| Kolom        | Isi                                |
| ------------ | ---------------------------------- |
| `video_id`   | ID YouTube (unik)                  |
| `title`      | judul lagu                         |
| `channel`    | channel/artis                      |
| `duration`   | durasi detik                       |
| `thumbnail`  | URL thumbnail                      |
| `file_name`  | nama file untuk download           |
| `file_size`  | ukuran byte                        |
| `created_at` | waktu dibuat                       |
| `updated_at` | waktu terakhir diubah              |

Tidak ada path absolut di database; file selalu dicari di folder aktif.

---

## Cara kerja singkat

**Pencarian**

```text
yt-dlp "ytsearch5:<query>" --flat-playlist --dump-json --no-warnings --ignore-errors
```

**Konversi**

```text
yt-dlp -f bestaudio/best -x --audio-format mp3 --audio-quality 0 --embed-metadata
       --no-playlist --newline -o <folder>/<id>.%(ext)s https://www.youtube.com/watch?v=<id>
```

- Konversi berjalan di thread pool di dalam proses Django (maksimal 2 worker).
- Progress download dipetakan ke 0–85, tahap convert 88, selesai 100.
- Job disimpan di memori; hasil akhirnya ditulis ke PostgreSQL dan sidecar `.json`.
- Frontend melakukan polling `GET /api/job/<id>` selama ada job aktif.

---

## Troubleshooting

| Masalah                              | Solusi                                                                    |
| ------------------------------------ | ------------------------------------------------------------------------- |
| `ffmpeg` tidak terdeteksi            | Install ffmpeg dan pastikan ada di `PATH`, lalu restart backend.          |
| Pencarian gagal / bot check          | Update yt-dlp (`py manage.py update_ytdlp`), coba lagi beberapa saat.     |
| Konversi error "Sign in to confirm"  | Video butuh login/usia, atau IP diblokir YouTube.                         |
| `database mati` di header            | Cek PostgreSQL, nama database, dan isi `.env`.                            |
| Frontend kosong di port 8137         | Jalankan `pnpm build` di folder `frontend`.                               |
| Port sudah dipakai                   | Hentikan proses lain atau ubah port Django + proxy Vite.                  |
| Preview tidak bisa di-seek           | Pastikan endpoint media mengembalikan `206` dan `Accept-Ranges: bytes`.   |
| Folder tidak bisa ditulis            | Gunakan path absolut yang bisa diakses user, atau pilih folder lain.      |
| Dialog pilih folder tidak muncul     | Hanya Windows + desktop interaktif; isi path manual sebagai alternatif.   |
| Nama lagu tidak terlihat di folder    | Baca sidecar `<videoId>.json` atau tag ID3 di MP3.                        |

Cek backend:

```powershell
curl.exe http://127.0.0.1:8137/api/health
```

Update engine:

```powershell
cd backend
py manage.py update_ytdlp
```

---

## Batasan & keamanan

- **Tanpa autentikasi** — aplikasi ini dirancang untuk lokal. Jangan langsung diekspos ke
  internet tanpa proteksi tambahan.
- **Job in-memory** — progress hilang saat backend restart; file dan koleksi tetap aman.
- **Bukan untuk multi-instance/serverless** — worker berjalan di proses Django.
- **Tidak ada rate limit** — hindari pemanggilan berlebihan.
- **Fitur Windows** — buka folder dan dialog pilih folder memakai Explorer/tkinter.
- **Hanya audio** — tanpa video dan tanpa playlist.
- **File tidak dihapus otomatis** — kelola lewat tombol hapus di koleksi.
- **Hak cipta** — gunakan hanya untuk konten yang kamu berhak; hormati ToS YouTube.

---

## Kontribusi

Pull request dan issue dipersilakan. Untuk perubahan besar, buka issue terlebih dahulu agar
bisa didiskusikan.
