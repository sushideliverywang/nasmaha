# Generated by Django 5.1.1 on 2024-10-26 22:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0007_rename_lowest_price_productmodel_discount_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productspec',
            name='value',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]