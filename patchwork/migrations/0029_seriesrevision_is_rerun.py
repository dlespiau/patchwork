# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-27 20:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0028_auto_20180220_2246'),
    ]

    operations = [
        migrations.AddField(
            model_name='seriesrevision',
            name='is_rerun',
            field=models.BooleanField(default=False),
        ),
    ]
