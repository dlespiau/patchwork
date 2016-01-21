# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def update_revision_test_state(apps, schema_editor):
    SeriesRevision = apps.get_model("patchwork", "SeriesRevision")
    TestResult = apps.get_model("patchwork", "TestResult")
    query =  SeriesRevision.objects.all()

    for _, revision in enumerate(query.iterator()):
        results = TestResult.objects.filter(revision=revision)
        if results.count() > 0:
            revision.test_state = max([r.state for r in results])
            revision.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0012_project_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='seriesrevision',
            name='test_state',
            field=models.SmallIntegerField(null=True, choices=[(0, b'pending'), (1, b'success'), (2, b'warning'), (3, b'failure')]),
        ),

        migrations.RunPython(update_revision_test_state, noop),
    ]
