# Generated by Django 5.1.1 on 2024-10-27 21:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0009_alter_productimage_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='productimage',
            name='hash',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]
