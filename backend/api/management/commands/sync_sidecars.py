from django.core.management.base import BaseCommand

from api import storage
from api.models import Track


class Command(BaseCommand):
    help = "Tulis sidecar JSON (<videoId>.json) untuk semua MP3 di library."

    def handle(self, *args, **options):
        written = 0
        missing = 0
        folder = storage.download_dir()

        for track in Track.objects.all():
            path = folder / f"{track.video_id}.mp3"
            if not path.exists() or path.stat().st_size < 1024:
                missing += 1
                continue

            storage.write_sidecar(
                {
                    "id": track.video_id,
                    "title": track.title,
                    "channel": track.channel,
                    "duration": track.duration,
                    "thumbnail": track.thumbnail,
                    "file_name": track.file_name,
                    "size": path.stat().st_size,
                },
                created_at=track.created_at.isoformat(),
            )
            written += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{written} sidecar ditulis di {folder}"
                + (f" ({missing} track tanpa file dilewati)" if missing else "")
            )
        )
