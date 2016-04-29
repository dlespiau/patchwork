# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def refresh_revision_test_state(apps, revision):
    TestResult = apps.get_model("patchwork", "TestResult")

    results = TestResult.objects.filter(revision=revision)
    if results.count() > 0:
        revision.test_state = max([r.state for r in results])
    else:
        revision.test_state = None

    revision.save()


def update_revision_state(apps, schema_editor):
    SeriesRevision = apps.get_model("patchwork", "SeriesRevision")

    query = SeriesRevision.objects.all()
    for _, revision in enumerate(query.iterator()):
        refresh_revision_test_state(apps, revision)


# We've inserted an 'info' state with a value of 1, so bump all non 0 test
# results by 1.
def migrate_results(apps, schema_editor):
    TestResult = apps.get_model("patchwork", "TestResult")

    query = TestResult.objects.all()
    for _, result in enumerate(query.iterator()):
        if result.state > 0:
            result.state += 1
            result.save()

    update_revision_state(apps, schema_editor)


# drop 'info' results and restore previous state values
def unmigrate_results(apps, schema_editor):
    TestResult = apps.get_model("patchwork", "TestResult")

    query = TestResult.objects.all()
    for _, result in enumerate(query.iterator()):
        if result.state == 1:
            result.delete()
            continue

        if result.state > 1:
            result.state -= 1
            result.save()

    update_revision_state(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0021_unselectable_maintainer_projects'),
    ]

    operations = [
        migrations.RunPython(migrate_results, unmigrate_results),

        migrations.AlterField(
            model_name='seriesrevision',
            name='test_state',
            field=models.SmallIntegerField(null=True, choices=[(0, b'pending'), (2, b'success'), (3, b'warning'), (4, b'failure'), (1, b'info')]),
        ),
        migrations.AlterField(
            model_name='testresult',
            name='state',
            field=models.SmallIntegerField(choices=[(0, b'pending'), (2, b'success'), (3, b'warning'), (4, b'failure'), (1, b'info')]),
        ),
    ]
