from django.db import models


class Track(models.Model):
    """Riwayat lagu yang sudah pernah dikonversi (sekaligus cache)."""

    video_id = models.CharField(max_length=16, unique=True)
    title = models.CharField(max_length=300)
    channel = models.CharField(max_length=200, blank=True, default="")
    duration = models.PositiveIntegerField(default=0)
    thumbnail = models.URLField(max_length=600, blank=True, default="")
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.video_id})"
