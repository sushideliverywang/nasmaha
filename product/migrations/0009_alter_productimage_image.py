# Generated by Django 5.1.1 on 2024-10-27 03:39

import product.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0008_alter_productspec_value'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productimage',
            name='image',
            field=models.ImageField(max_length=500, upload_to=product.models.product_image_upload_path),
        ),
    ]
