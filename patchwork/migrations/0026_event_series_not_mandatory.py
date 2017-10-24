# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0025_patch_last_updated'),
    ]

    operations = [
        migrations.AlterField(
            model_name='EventLog',
            name='series',
            field=models.ForeignKey(to='patchwork.Series', null=True),
        ),
    ]
