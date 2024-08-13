# Generated by Django 4.2.14 on 2024-08-13 13:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("viewer", "0004_remove_person_viewer_pers_nicknam_04dc21_idx_and_more"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="eventsimilarity",
            name="viewer_even_diff_va_d6965d_idx",
        ),
        migrations.RenameField(
            model_name="eventsimilarity",
            old_name="diff_value",
            new_name="route_diff",
        ),
        migrations.AddIndex(
            model_name="eventsimilarity",
            index=models.Index(
                fields=["route_diff"], name="viewer_even_route_d_a36dfb_idx"
            ),
        ),
    ]
