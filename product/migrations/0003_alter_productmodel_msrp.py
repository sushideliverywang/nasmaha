# Generated by Django 5.1.1 on 2024-10-19 19:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0002_productmodel_link'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productmodel',
            name='msrp',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
