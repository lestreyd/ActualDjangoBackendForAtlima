# Generated by Django 3.2.15 on 2022-08-13 21:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('location', '0002_alter_citytranslation_title'),
    ]

    operations = [
        migrations.AlterField(
            model_name='countrytranslation',
            name='title',
            field=models.CharField(max_length=255),
        ),
    ]
