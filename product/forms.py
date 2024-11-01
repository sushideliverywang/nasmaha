from django.core.exceptions import ValidationError
from django import forms
from .models import Brand, Category, ProductModel

class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name','description', 'website', 'logo']  # Add other fields if needed
        widgets = {
            'name': forms.TextInput(attrs={"class":"form-control"}),
            'description': forms.Textarea(attrs={"class":"form-control"}),
            'website':forms.TextInput(attrs={"class":"form-control"}),
            'logo':forms.FileInput(attrs={"class":"form-control image-file"}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent_category']
        widgets = {
            'name': forms.TextInput(attrs={"class":"form-control"}),
            'parent_category': forms.Select(attrs={"class": "form-control", "data-style":"py-0"}),
        }

class ProductModelForm(forms.ModelForm):
    class Meta:
        model = ProductModel
        fields = ['model_number', 'description', 'msrp', 'brand', 'category', 'discount_price','link']
        widgets = {
           'model_number':forms.TextInput(attrs={"class":"form-control"}),
           'description':forms.Textarea(attrs={"class":"form-control"}),
           'brand': forms.Select(attrs={"class": "form-control", "data-style":"py-0"}),
           'category':forms.Select(attrs={"class": "form-control", "data-style":"py-0"}),
           'msrp': forms.NumberInput(attrs={"class":"form-control"}),
           'discount_price': forms.NumberInput(attrs={"class":"form-control"}),
           'link': forms.URLInput(attrs={"class":"form-control"}),
        }
    # Validate model_number for uniqueness
    def clean_model_number(self):
        model_number = self.cleaned_data.get('model_number')

        # When editing, ignore the current instance's model_number in the uniqueness check
        if ProductModel.objects.filter(model_number=model_number).exclude(pk=self.instance.pk).exists():
            raise ValidationError(f"The model number '{model_number}' already exists. Please enter a unique one.")

        return model_number

    def __init__(self, *args, **kwargs):
        super(ProductModelForm, self).__init__(*args, **kwargs)
        
        # If the form is being used for editing (i.e., an instance exists), make model_number read-only
        if self.instance.pk:
            self.fields['model_number'].widget.attrs['readonly'] = True

