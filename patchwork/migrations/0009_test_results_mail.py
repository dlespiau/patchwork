# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0008_test_results'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='mail_condition',
            field=models.SmallIntegerField(default=0, choices=[(0, b'always'), (0, b'on failure')]),
        ),
        migrations.AddField(
            model_name='test',
            name='mail_recipient',
            field=models.SmallIntegerField(default=0, choices=[(0, b'none'), (1, b'submitter'), (2, b'mailing list')]),
        ),
    ]
