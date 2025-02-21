import os
import logging
from django.db import transaction
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
import django_rq

from .models import Video
from .tasks import remove_file_task, convert_to_120p, convert_to_360p, convert_to_720p, convert_to_1080p

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    if created:
        try:
            # Get the video file name and base name
            video_file_name = os.path.basename(instance.video_file.name)
            base_name, ext = os.path.splitext(video_file_name)

            # Generate relative paths for converted files
            relative_paths = [
                os.path.join(settings.MEDIA_URL, 'videos',
                             f'{base_name}_120p{ext}'),
                os.path.join(settings.MEDIA_URL, 'videos',
                             f'{base_name}_360p{ext}'),
                os.path.join(settings.MEDIA_URL, 'videos',
                             f'{base_name}_720p{ext}'),
                os.path.join(settings.MEDIA_URL, 'videos',
                             f'{base_name}_1080p{ext}'),
            ]

            # Conversion map for resolutions
            resolution_map = {
                '120p': convert_to_120p,
                '360p': convert_to_360p,
                '720p': convert_to_720p,
                '1080p': convert_to_1080p,
            }

            # Normalize paths for the database
            instance.converted_files = [path.replace(
                "\\", "/") for path in relative_paths]

            # Save the database entry first
            instance.save()

            # Add the conversion jobs to the queue
            queue = django_rq.get_queue('default')
            for path in relative_paths:
                resolution = os.path.splitext(path)[0].split('_')[-1]
                if resolution in resolution_map:
                    queue.enqueue(
                        resolution_map[resolution], instance.video_file.path)

            # Remove the original video file after conversion tasks are queued
            if instance.video_file and os.path.isfile(instance.video_file.path):
                os.remove(instance.video_file.path)

        except Exception as e:
            logger.error(f"Error during video post-save processing: {e}")


@receiver(post_delete, sender=Video)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    queue = django_rq.get_queue('default')

    if instance.video_file:
        # Queue für das Löschen der Originaldatei
        queue.enqueue(remove_file_task, instance.video_file.path)

        base_path, ext = os.path.splitext(instance.video_file.path)
        converted_files = [
            f"{base_path}_120p{ext}",
            f"{base_path}_360p{ext}",
            f"{base_path}_720p{ext}",
            f"{base_path}_1080p{ext}",
        ]
        # Queue für das Löschen der konvertierten Dateien
        for file in converted_files:
            queue.enqueue(remove_file_task, file)

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

    # Wenn die Datei geändert wurde, lösche die alte
    if old_instance.video_file and old_instance.video_file != instance.video_file:
        queue = django_rq.get_queue('default')

        # Queue für das Löschen der alten Videodatei
        queue.enqueue(remove_file_task, old_instance.video_file.path)

        base_path, ext = os.path.splitext(old_instance.video_file.path)
        converted_files = [
            f"{base_path}_120p{ext}",
            f"{base_path}_360p{ext}",
            f"{base_path}_720p{ext}",
            f"{base_path}_1080p{ext}",
        ]
        # Queue für das Löschen der konvertierten Dateien
        for file in converted_files:
            queue.enqueue(remove_file_task, file)
