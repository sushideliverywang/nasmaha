from django.db import models
from product.models import ProductModel

class Vendor(models.Model):
    vendor_id = models.AutoField(primary_key=True)
    vendor_name = models.CharField(max_length=100)
    contact_info = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.vendor_name

class InventoryItem(models.Model):
    CONDITION_CHOICES = [
        ('B_NEW', 'Brand New'),
        ('NEW_SD', 'New Scratch&Dent'),
        ('USED', 'Used'),
        ('REFURB', 'Refurbished'),
    ]

    WARRANTY_CHOICES = [
        ('STORE_1', 'Store One Year'),
        ('STORE_90', 'Store 90 Days'),
        ('STORE_30', 'Store 30 Days'),
        ('STORE_2', 'Store Two Years'),
        ('STORE_3', 'Store Three Years'),
        ('STORE_4', 'Store Four Years'),
        ('STORE_5', 'Store Five Years'),
        ('MANUF_1', 'Manufacturer One Year'),
        ('CPS_1',  'CPS One Year'),
        ('CPS_2',  'CPS Two Years'),
        ('CPS_3',  'CPS Three Years'),
        ('CPS_4',  'CPS Four Years'),
        ('NONE', 'None'),
    ]

    STATE_CHOICES = [
        ('RECEIV', 'Receiving'),
        ('TEST', 'Testing'),
        ('SCRAP', 'Scrap'),
        ('IN_STOCK', 'In Stock'),
        ('SOLD', 'Sold'),
        ('RETURNED', 'Returned'),
    ]

    inventory_item_id = models.AutoField(primary_key=True)
    product_model = models.ForeignKey(ProductModel, on_delete=models.CASCADE)
    serial_number = models.CharField(max_length=100)
    control_number = models.CharField(max_length=100)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES)
    retail_price = models.DecimalField(max_digits=10, decimal_places=2)
    warranty_type = models.CharField(max_length=10, choices=WARRANTY_CHOICES)
    current_state = models.CharField(max_length=10, choices=STATE_CHOICES)
    purchase_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.control_number} - {self.product_model}"
