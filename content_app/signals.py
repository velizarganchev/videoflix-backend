import os
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import Video
from .tasks import convert_to_120p, convert_to_360p, convert_to_720p, convert_to_1080p


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    print('Video post save signal')
    if created:
        convert_to_120p(instance.video_file.path)
        convert_to_360p(instance.video_file.path)
        convert_to_720p(instance.video_file.path)
        convert_to_1080p(instance.video_file.path)
        
        try:
            if instance.video_file and os.path.isfile(instance.video_file.path):
                os.remove(instance.video_file.path)
        except Exception as e:
            print(f"Error deleting original file: {e}")


@receiver(post_delete, sender=Video)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes all associated files from the filesystem
    when the corresponding `Video` object is deleted.
    """
    try:
        if instance.video_file and os.path.isfile(instance.video_file.path):
            os.remove(instance.video_file.path)
    except Exception as e:
        print(f"Error deleting original file: {e}")

    base_path, ext = os.path.splitext(instance.video_file.path)
    converted_files = [
        f"{base_path}_120p{ext}",
        f"{base_path}_360p{ext}",
        f"{base_path}_720p{ext}",
        f"{base_path}_1080p{ext}",
    ]

    for file_path in converted_files:
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")


@receiver(pre_save, sender=Video)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """
    Deletes old file from filesystem
    when corresponding `Video` object is updated
    with new file.
    """
    if not instance.pk:
        return

    try:
        old_file = Video.objects.get(pk=instance.pk).video_file
    except Video.DoesNotExist:
        return

    new_file = instance.video_file
    if old_file and old_file != new_file:
        try:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)
        except Exception as e:
            print(f"Error deleting old file: {e}")
