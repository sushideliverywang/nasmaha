# Generated by Django 5.1.1 on 2024-10-25 03:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0006_spec_productspec'),
    ]

    operations = [
        migrations.RenameField(
            model_name='productmodel',
            old_name='lowest_price',
            new_name='discount_price',
        ),
    ]