# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('patchwork', '0007_multiple_projects_same_ml'),
    ]

    operations = [
        migrations.CreateModel(
            name='Test',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('project', models.ForeignKey(to='patchwork.Project', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='TestResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(default=datetime.datetime.now)),
                ('state', models.SmallIntegerField(choices=[(0, b'pending'), (1, b'success'), (2, b'warning'), (3, b'failure')])),
                ('url', models.URLField(null=True, blank=True)),
                ('summary', models.TextField(null=True, blank=True)),
                ('patch', models.ForeignKey(blank=True, to='patchwork.Patch', null=True, on_delete=models.CASCADE)),
                ('revision', models.ForeignKey(blank=True, to='patchwork.SeriesRevision', null=True, on_delete=models.CASCADE)),
                ('test', models.ForeignKey(to='patchwork.Test', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='testresult',
            unique_together=set([('test', 'patch'), ('test', 'revision')]),
        ),
        migrations.AlterUniqueTogether(
            name='test',
            unique_together=set([('project', 'name')]),
        ),
    ]
