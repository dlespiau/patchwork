# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0006_eventlog_parameters'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='subject_prefix_tags',
            field=models.CharField(help_text=b'Comma separated list of tags', max_length=255, blank=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='listid',
            field=models.CharField(max_length=255),
        ),
    ]
