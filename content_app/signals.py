import os
import logging
from django.db import transaction
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
import django_rq

from .models import Video
from .tasks import (
    remove_file_task,
    convert_to_120p,
    convert_to_360p,
    convert_to_720p,
    convert_to_1080p,
    delete_original_video_task,  # 👈 neue Task
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    if created and not instance.converted_files:
        try:
            with transaction.atomic():
                # Videodateiname ermitteln
                video_file_name = os.path.basename(instance.video_file.name)
                base_name, ext = os.path.splitext(video_file_name)

                # Pfade (URL) für die Datenbank speichern
                relative_urls = [
                    os.path.join(settings.MEDIA_URL, 'videos', f'{base_name}_120p{ext}'),
                    os.path.join(settings.MEDIA_URL, 'videos', f'{base_name}_360p{ext}'),
                    os.path.join(settings.MEDIA_URL, 'videos', f'{base_name}_720p{ext}'),
                    os.path.join(settings.MEDIA_URL, 'videos', f'{base_name}_1080p{ext}'),
                ]
                instance.converted_files = [url.replace("\\", "/") for url in relative_urls]
                instance.save()

                # Tasks einreihen
                resolution_map = {
                    '120p': convert_to_120p,
                    '360p': convert_to_360p,
                    '720p': convert_to_720p,
                    '1080p': convert_to_1080p,
                }

                queue = django_rq.get_queue('default')
                for resolution, task_func in resolution_map.items():
                    queue.enqueue(task_func, instance.video_file.path)

                # ✅ Originaldatei erst löschen, wenn Konvertierung abgeschlossen
                queue.enqueue(delete_original_video_task, instance.video_file.path)

        except Exception as e:
            logger.error(f"Fehler bei post_save-Verarbeitung: {e}")


@receiver(post_delete, sender=Video)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    queue = django_rq.get_queue('default')

    if instance.video_file:
        queue.enqueue(remove_file_task, instance.video_file.path)

        base_path, ext = os.path.splitext(instance.video_file.path)
        converted_files = [
            f"{base_path}_120p{ext}",
            f"{base_path}_360p{ext}",
            f"{base_path}_720p{ext}",
            f"{base_path}_1080p{ext}",
        ]
        for file_path in converted_files:
            queue.enqueue(remove_file_task, file_path)

    if instance.image_file:
        queue.enqueue(remove_file_task, instance.image_file.path)


@receiver(pre_save, sender=Video)
def auto_delete_file_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_instance = Video.objects.get(pk=instance.pk)
    except Video.DoesNotExist:
        return

    if old_instance.video_file and old_instance.video_file != instance.video_file:
        queue = django_rq.get_queue('default')

        queue.enqueue(remove_file_task, old_instance.video_file.path)

        base_path, ext = os.path.splitext(old_instance.video_file.path)
        converted_files = [
            f"{base_path}_120p{ext}",
            f"{base_path}_360p{ext}",
            f"{base_path}_720p{ext}",
            f"{base_path}_1080p{ext}",
        ]
        for file_path in converted_files:
            queue.enqueue(remove_file_task, file_path)
