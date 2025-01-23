# Generated by Django 4.2.16 on 2025-01-22 16:34

import colorfield.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("viewer", "0010_importedfile_activity"),
    ]

    operations = [
        migrations.CreateModel(
            name="PhotoTag",
            fields=[
                (
                    "id",
                    models.SlugField(max_length=32, primary_key=True, serialize=False),
                ),
                ("comment", models.TextField(blank=True, null=True)),
                (
                    "colour",
                    colorfield.fields.ColorField(
                        default="#777777", image_field=None, max_length=25, samples=None
                    ),
                ),
                (
                    "photos",
                    models.ManyToManyField(related_name="tags", to="viewer.photo"),
                ),
            ],
            options={
                "verbose_name": "photo tag",
                "verbose_name_plural": "photo tags",
            },
        ),
    ]
