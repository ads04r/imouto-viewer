# Generated by Django 4.2.14 on 2024-08-20 12:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("viewer", "0007_importedfile_earliest_timestamp_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="schemaorgclass",
            name="parent",
        ),
        migrations.CreateModel(
            name="SchemaOrgRelation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "broader",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="relations_narrower",
                        to="viewer.schemaorgclass",
                    ),
                ),
                (
                    "narrower",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="relations_broader",
                        to="viewer.schemaorgclass",
                    ),
                ),
            ],
            options={
                "verbose_name": "schema.org relation",
                "verbose_name_plural": "schema.org relations",
            },
        ),
    ]