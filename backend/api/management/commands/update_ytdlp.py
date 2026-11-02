from django.conf import settings
from django.core.management.base import BaseCommand

from api import ytdlp


class Command(BaseCommand):
    help = "Unduh / perbarui binary yt-dlp ke folder bin/"

    def handle(self, *args, **options):
        path = ytdlp.ensure_ytdlp(force=True)
        self.stdout.write(self.style.SUCCESS(f"yt-dlp tersimpan di {path}"))
        self.stdout.write(f"versi: {ytdlp.version() or 'tidak diketahui'}")
        ffmpeg = ytdlp.find_ffmpeg()
        self.stdout.write(f"ffmpeg: {ffmpeg or 'TIDAK DITEMUKAN (install: winget install Gyan.FFmpeg)'}")
        self.stdout.write(f"download dir: {settings.DOWNLOAD_DIR}")
