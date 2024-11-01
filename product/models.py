from django.db import models
from django.utils.text import slugify
import os


# Create your models here.
class Brand(models.Model):
    brand_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    logo = models.ImageField(upload_to='brand_logos/', null=True, blank=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    parent_category = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='subcategories')

    def __str__(self):
        return self.name

class ProductModel(models.Model):
    product_model_id = models.AutoField(primary_key=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    model_number = models.CharField(max_length=100, unique=True, blank=False, null=False)
    description = models.TextField(blank=True)
    msrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_price = models.DecimalField(max_digits=10,decimal_places=2, null=True, blank=True)
    link = models.URLField(max_length=500, null=True, blank=True)  # URLField to store the product URL

    def __str__(self):
        return self.model_number

def product_image_upload_path(model_number, filename):
    # Construct the folder path relative to MEDIA_ROOT
    return os.path.join('product_model_images', model_number, filename)

class ProductImage(models.Model):
    product_image_id = models.AutoField(primary_key=True)
    product_model = models.ForeignKey(ProductModel, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=product_image_upload_path, max_length=500)
    hash = models.CharField(max_length=32, null=True, blank=True)  # Add a hash field for duplicate detection

    def __str__(self):
        return f"Image for {self.product_model.model_number}"

class Spec(models.Model):
    spec_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class ProductSpec(models.Model):
    product_spec_id = models.AutoField(primary_key=True)  # Renamed product_feature_id
    product_model = models.ForeignKey(ProductModel, on_delete=models.CASCADE)
    spec = models.ForeignKey(Spec, on_delete=models.CASCADE)  # Renamed feature to specification
    value = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return f"{self.product_model} - {self.spec} - {self.value}"
