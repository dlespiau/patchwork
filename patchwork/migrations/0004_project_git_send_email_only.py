# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0003_series'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='git_send_email_only',
            field=models.BooleanField(default=False),
        ),
    ]
