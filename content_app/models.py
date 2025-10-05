from django.db import models
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image
import os
import io
import tempfile  # NEW

# Ако ще генерираш thumbnail локално, MoviePy е тежък; по-добре в worker
try:
    from moviepy import VideoFileClip
except Exception:
    VideoFileClip = None  # за да не гърми при липса

# --- ЯВНО ФОРСИРАМЕ S3 STORAGE ЗА ТЕЗИ ПОЛЕТА ---
try:
    from storages.backends.s3boto3 import S3Boto3Storage
    s3_storage = S3Boto3Storage()
except Exception:
    # fallback – ако по някаква причина липсва django-storages (не би трябвало)
    from django.core.files.storage import FileSystemStorage
    s3_storage = FileSystemStorage()

LIST_OF_GENRES = [
    ('Action', 'Action'),
    ('Adventure', 'Adventure'),
    ('Comedy', 'Comedy'),
    ('Crime', 'Crime'),
    ('Drama', 'Drama'),
    ('Fantasy', 'Fantasy'),
    ('Historical', 'Historical'),
    ('Horror', 'Horror'),
    ('Mystery', 'Mystery'),
    ('Philosophical', 'Philosophical'),
    ('Political', 'Political'),
    ('Romance', 'Romance'),
    ('Science fiction', 'Science fiction'),
    ('Thriller', 'Thriller'),
    ('Western', 'Western'),
    ('Animation', 'Animation'),
    ('Documentary', 'Documentary'),
    ('Biographical', 'Biographical'),
    ('Educational', 'Educational'),
    ('Erotic', 'Erotic'),
    ('Musical', 'Musical'),
    ('Reality', 'Reality'),
    ('Sports', 'Sports'),
    ('Superhero', 'Superhero'),
    ('Surreal', 'Surreal'),
    ('Other', 'Other'),
]


class Video(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    category = models.CharField(
        max_length=50, choices=LIST_OF_GENRES, blank=True, null=True
    )

    # >>> ТУК форсираме S3 storage <<<
    image_file = models.ImageField(
        storage=s3_storage, upload_to='images', blank=True, null=True
    )
    video_file = models.FileField(
        storage=s3_storage, upload_to='videos', blank=True, null=True
    )

    # ВАЖНО: вместо list -> dict { "360p": "videos/..._360p.mp4", ... }
    converted_files = models.JSONField(blank=True, null=True, default=dict)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"({self.id}) {self.title} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"

    # ---- helpers for S3 keys ----
    QUALITIES = ("120p", "360p", "720p", "1080p")

    def base_path_and_ext(self):
        """
        Връща (base_path, ext) от self.video_file.name
        example: 'videos/123/video.mp4' -> ('videos/123/video', '.mp4')
        """
        if not self.video_file:
            return None, None
        base_path, ext = os.path.splitext(self.video_file.name)
        return base_path, ext

    def build_converted_map(self):
        """
        Генерира dict с ключове за всички качества ОТ оригиналния ключ.
        Не качва/създава файлове, просто генерира имена.
        """
        base, ext = self.base_path_and_ext()
        if not base:
            return {}
        return {q: f"{base}_{q}{ext}" for q in self.QUALITIES}

    def get_key_for_quality(self, quality: str | None = None):
        """
        Връща S3 key (или storage key) за подаденото качество.
        Ако няма converted_files — генерира от името на оригинала.
        Ако quality е None -> връща оригиналния ключ (self.video_file.name).
        """
        if not self.video_file:
            return None

        if not quality:
            return self.video_file.name

        # ако вече имаме dict в БД, ползвай него
        if isinstance(self.converted_files, dict) and quality in self.converted_files:
            return self.converted_files[quality]

        # иначе построи on-the-fly от оригинала
        base, ext = self.base_path_and_ext()
        if not base:
            return None
        return f"{base}_{quality}{ext}"

    # ---- thumbnail generation ----
    def save(self, *args, **kwargs):
        """
        1) Нормализира converted_files към dict.
        2) При СЪЗДАВАНЕ (няма pk), ако има video_file и няма image_file:
           - копира upload потока във временен файл;
           - вади кадър (1.0s) чрез MoviePy и го записва като JPEG в image_file (S3);
           - връща указателя на video_file в начало, за да се качи коректно.
        3) Записва модела нормално.
        """
        # 1) нормализирай converted_files към dict
        if not self.converted_files or isinstance(self.converted_files, list):
            self.converted_files = self.build_converted_map()

        creating = self.pk is None
        need_thumb = creating and self.video_file and not self.image_file

        tmp_path = None
        if need_thumb:
            try:
                # вземи file-like обекта от полето
                fileobj = self.video_file

                # направи временен локален файл от upload stream-а
                suffix = os.path.splitext(getattr(fileobj, "name", "video.mp4"))[
                    1] or ".mp4"
                fd, tmp_path = tempfile.mkstemp(suffix=suffix)
                with os.fdopen(fd, "wb") as tmpf:
                    if hasattr(fileobj, "chunks"):
                        for chunk in fileobj.chunks():
                            tmpf.write(chunk)
                    else:
                        tmpf.write(fileobj.read())

                # генерирай thumbnail само ако има MoviePy
                if VideoFileClip:
                    self._generate_thumbnail_local(tmp_path, time_sec=1.0)

                # върни указателя на upload файла в началото –
                # важно, иначе storage може да качи полу-празен файл
                try:
                    fileobj.seek(0)
                except Exception:
                    pass

            except Exception as e:
                # не прекъсвай save при проблем с тъмбнейла
                print(f"Thumbnail generation skipped: {e}")
            finally:
                if tmp_path:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

        # 3) стандартният save
        super().save(*args, **kwargs)

    def _generate_thumbnail_local(self, video_path: str, time_sec: float = 1.0):
        """
        Генерира thumbnail от ЛОКАЛЕН video_path и качва в self.image_file.
        Работи независимо от това, че финалният storage е S3,
        защото image_file.save() използва свързания бекенд.
        """
        try:
            # Име на JPEG-а близо до видеото, но в нашата upload_to('images')
            base_name = os.path.splitext(
                os.path.basename(self.video_file.name))[0]
            thumb_name = f"{base_name}.jpg"

            clip = VideoFileClip(video_path)
            frame = clip.get_frame(time_sec)
            image = Image.fromarray(frame)

            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            buf.seek(0)

            # запиши в ImageField (ще отиде в S3, защото полето е с s3_storage)
            self.image_file.save(
                thumb_name,
                ContentFile(buf.read()),
                save=False  # важно: да не влизаме в рекурсивни save()
            )
        except Exception as e:
            # лог по желание
            print(f"Thumbnail generation failed: {e}")
