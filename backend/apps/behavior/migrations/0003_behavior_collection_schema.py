from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("behavior", "0002_keystrokeevent_client_event_id_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.DeleteModel(name="KeystrokeEvent"),
        migrations.DeleteModel(name="MouseEvent"),
        migrations.RemoveIndex(
            model_name="behaviorsession",
            name="behavior_be_user_id_f18731_idx",
        ),
        migrations.RemoveIndex(
            model_name="behaviorsession",
            name="behavior_be_session_86362c_idx",
        ),
        migrations.RenameField(
            model_name="behaviorsession",
            old_name="session_token",
            new_name="session_key",
        ),
        migrations.AlterField(
            model_name="behaviorsession",
            name="session_key",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name="behaviorsession",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="behavior_sessions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="behaviorsession",
            name="ip_address",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="behaviorsession",
            name="context",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterModelOptions(
            name="behaviorsession",
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="KeystrokeEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("keydown", "Key down"),
                            ("keyup", "Key up"),
                        ],
                        max_length=16,
                    ),
                ),
                ("key_code", models.CharField(blank=True, max_length=64)),
                ("key_value_hash", models.CharField(blank=True, max_length=128)),
                ("timestamp_ms", models.BigIntegerField()),
                ("relative_time_ms", models.IntegerField()),
                ("dwell_time_ms", models.IntegerField(blank=True, null=True)),
                ("flight_time_ms", models.IntegerField(blank=True, null=True)),
                ("metadata", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "behavior_session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="keystroke_events",
                        to="behavior.behaviorsession",
                    ),
                ),
            ],
            options={
                "ordering": ["timestamp_ms", "id"],
                "indexes": [
                    models.Index(
                        fields=["behavior_session", "timestamp_ms"],
                        name="behavior_ke_behavio_3562f4_idx",
                    ),
                    models.Index(
                        fields=["event_type"],
                        name="behavior_ke_event_t_1197c1_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="MouseEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("move", "Move"),
                            ("click", "Click"),
                            ("scroll", "Scroll"),
                        ],
                        max_length=16,
                    ),
                ),
                ("x", models.IntegerField(blank=True, null=True)),
                ("y", models.IntegerField(blank=True, null=True)),
                ("button", models.CharField(blank=True, max_length=32)),
                ("scroll_delta_x", models.FloatField(blank=True, null=True)),
                ("scroll_delta_y", models.FloatField(blank=True, null=True)),
                ("timestamp_ms", models.BigIntegerField()),
                ("relative_time_ms", models.IntegerField()),
                ("metadata", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "behavior_session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mouse_events",
                        to="behavior.behaviorsession",
                    ),
                ),
            ],
            options={
                "ordering": ["timestamp_ms", "id"],
                "indexes": [
                    models.Index(
                        fields=["behavior_session", "timestamp_ms"],
                        name="behavior_mo_behavio_8e32a9_idx",
                    ),
                    models.Index(
                        fields=["event_type"],
                        name="behavior_mo_event_t_67b729_idx",
                    ),
                ],
            },
        ),
        migrations.AlterModelOptions(
            name="behaviorsession",
            options={"ordering": ["-started_at"]},
        ),
        migrations.AddIndex(
            model_name="behaviorsession",
            index=models.Index(
                fields=["user", "started_at"],
                name="behavior_be_user_id_f18731_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="behaviorsession",
            index=models.Index(
                fields=["session_key"],
                name="behavior_be_session_0a653c_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="behaviorsession",
            index=models.Index(
                fields=["started_at"],
                name="behavior_be_started_cb8aa1_idx",
            ),
        ),
    ]
