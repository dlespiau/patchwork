# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def update_last_revision_n_patches(apps, schema_editor):
    Series = apps.get_model("patchwork", "Series")
    SeriesRevision = apps.get_model("patchwork", "SeriesRevision")

    query =  Series.objects.all()
    for _, series in enumerate(query.iterator()):
        revisions = SeriesRevision.objects.filter(series=series). \
                    order_by('version').reverse()

        for field in series._meta.local_fields:
            if field.name == "last_updated":
                field.auto_now = False

        series.last_revision = revisions[0]
        series.save()

        for field in series._meta.local_fields:
            if field.name == "last_updated":
                field.auto_now = True

        for revision in revisions:
            revision.n_patches = series.n_patches
            revision.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0013_seriesrevision_test_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='series',
            name='last_revision',
            field=models.OneToOneField(related_name='+', null=True, to='patchwork.SeriesRevision', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='seriesrevision',
            name='n_patches',
            field=models.IntegerField(default=0),
        ),

        migrations.RunPython(update_last_revision_n_patches, noop),
    ]
