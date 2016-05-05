# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def set_auto_now(obj, field_name, enable):
    for field in obj._meta.local_fields:
        if field.name == field_name:
            field.auto_now = enable


def noop(apps, schema_editor):
    pass


def set_patch_last_updated(apps, schema_editor):
    Patch = apps.get_model("patchwork", "Patch")

    query = Patch.objects.all()
    for _, patch in enumerate(query.iterator()):
        patch.last_updated = patch.date
        set_auto_now(patch, "last_updated", False)
        patch.save()
        set_auto_now(patch, "last_updated", True)


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0024_blank_test_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='patch',
            name='last_updated',
            field=models.DateTimeField(auto_now=True, null=True),
        ),

        migrations.RunPython(set_patch_last_updated, noop),

        migrations.AlterField(
            model_name='patch',
            name='last_updated',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
