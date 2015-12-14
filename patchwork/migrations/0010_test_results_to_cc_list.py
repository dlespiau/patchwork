# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0009_test_results_mail'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='mail_cc_list',
            field=models.CharField(help_text=b'Comma separated list of emails', max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='test',
            name='mail_to_list',
            field=models.CharField(help_text=b'Comma separated list of emails', max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='test',
            name='mail_recipient',
            field=models.SmallIntegerField(default=0, choices=[(0, b'none'), (1, b'submitter'), (2, b'mailing list'), (3, b'recipient list')]),
        ),
    ]
