# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def noop(apps, schema_editor):
    pass


def update_version_n_patches(apps, schema_editor):
    Series = apps.get_model("patchwork", "Series")
    SeriesRevision = apps.get_model("patchwork", "SeriesRevision")

    query =  Series.objects.all()
    for _, series in enumerate(query.iterator()):
        revisions = SeriesRevision.objects.filter(series=series). \
                    order_by('version').reverse()
        last_revision = revisions[0]

        for field in series._meta.local_fields:
            if field.name == "last_updated":
                field.auto_now = False

        series.version = last_revision.version
        series.n_patches = last_revision.n_patches
        series.save()

        for field in series._meta.local_fields:
            if field.name == "last_updated":
                field.auto_now = True


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0014_last_revision'),
    ]

    operations = [
        migrations.RunPython(noop, update_version_n_patches),

        migrations.RemoveField(
            model_name='series',
            name='n_patches',
        ),
        migrations.RemoveField(
            model_name='series',
            name='version',
        ),
    ]
