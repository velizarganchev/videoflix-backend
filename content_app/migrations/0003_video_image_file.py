# Generated by Django 5.1.4 on 2025-01-11 09:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content_app', '0002_alter_video_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='image_file',
            field=models.ImageField(blank=True, null=True, upload_to='images'),
        ),
    ]