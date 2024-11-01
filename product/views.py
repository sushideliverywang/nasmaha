import os
import csv
import json
from django.shortcuts import render, redirect, get_object_or_404
from .models import Brand, Category, ProductModel, ProductImage, product_image_upload_path, ProductSpec, Spec
from .forms import BrandForm, CategoryForm, ProductModelForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .scraper_main import scraper_enter, open_lg_sub_page
from django.core.files.storage import FileSystemStorage
import hashlib
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging

# Create your views here.
@login_required
def brand_list(request):
    brands = Brand.objects.all()
    return render(request, 'product/brand_list.html', {'brands': brands})
@login_required
def brand_add(request):
    if request.method == 'POST':
        form = BrandForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('brand_list')
    else:
        form = BrandForm()
    return render(request, 'product/brand_form.html', {'form': form})
@login_required
def brand_edit(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        form = BrandForm(request.POST, request.FILES, instance=brand)
        if form.is_valid():
            form.save()
            return redirect('brand_list')
    else:
        form = BrandForm(instance=brand)
    return render(request, 'product/brand_form.html', {'form': form})
@login_required
def brand_delete(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        brand.delete()
        return redirect('brand_list')
    return render(request, 'product/brand_confirm_delete.html', {'brand': brand})

@login_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'product/category_list.html', {'categories': categories})
@login_required
def category_add(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'product/category_form.html', {'form': form})
@login_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'product/category_form.html', {'form': form})
@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        return redirect('category_list')
    return render(request, 'product/category_confirm_delete.html', {'category': category})

@login_required
def product_model_list(request):
    # 获取所有产品型号
    product_model = ProductModel.objects.all()
    
    # 获取所有品牌名称（去重）
    brands = Brand.objects.values_list('name', flat=True).distinct()
    
    # 获取所有分类，包括父子关系
    categories = Category.objects.all()

    # 构建分类的父子关系字典
    category_dict = {}
    for category in categories:
        if category.parent_category is None:
            category_dict[category] = category.subcategories.all()

    # 将产品型号、品牌和分类字典传递给模板
    context = {
        'product_model': product_model,
        'brands': brands,
        'categories': categories,  # 传递所有分类给前端模板
        'category_dict': category_dict,
    }


    return render(request, "product/product_model_list.html", context)

@login_required
def product_model_add(request):
    if request.method == 'POST':
        form = ProductModelForm(request.POST)
        if form.is_valid():
            # Save the product model first
            product_model = form.save()
            
            images = request.FILES.getlist('images')
            if images:
                # Loop through the uploaded images
                fs = FileSystemStorage()  # Create an instance of FileSystemStorage for handling file storage
                for image in images:
                    # Generate a unique hash for the image content
                    image_hash = hashlib.md5(image.read()).hexdigest()
                    image.seek(0)  # Reset file pointer after reading

                    # Create a unique image file name using the hash
                    image_file_name = f"{product_model.model_number}_{image_hash}.jpg"

                    # Save the image using FileSystemStorage, which ensures proper path handling
                    saved_image_path = fs.save(product_image_upload_path(product_model.model_number, image_file_name), image)

                    # Create ProductImage entry, saving the relative path to MEDIA_ROOT
                    ProductImage.objects.create(
                        product_model=product_model,
                        image=saved_image_path,
                        hash=image_hash
                    )

            # Redirect to the product model list page
            return redirect('product_model_list')
    else:
        form = ProductModelForm()

    # Render the product model form template
    return render(request, 'product/product_model_form.html', {
        'form': form,
    })

@login_required
def product_model_edit(request, pk):
    # 1. Fetch the specific ProductModel from the database
    product_model = get_object_or_404(ProductModel, pk=pk)
    existing_images = ProductImage.objects.filter(product_model=product_model)
    
    # 2. Check if the request is POST (form submission)
    if request.method == 'POST':
        # Bind form data with files (for image upload) to the form
        form = ProductModelForm(request.POST, request.FILES, instance=product_model)
        
        # 3. Check if the form is valid (i.e., all fields have valid data)
        if form.is_valid():
            # Save the form data (this updates the ProductModel instance)
            product_model = form.save()

            images = request.FILES.getlist('images')
            if images:
                fs = FileSystemStorage()  # Use FileSystemStorage for proper file handling
                for image in images:

                    image_hash = hashlib.md5(image.read()).hexdigest()
                    image.seek(0)  # Reset file pointer after reading
                    duplicate = ProductImage.objects.filter(product_model=product_model, hash=image_hash).exists()
                    if duplicate:
                        print(f"Duplicate image found for model {product_model.model_number}, skipping upload.")
                        continue
                    
                    # Use product_model instance and image name with hash to generate the correct file path
                    image_file_name = f"{product_model.model_number}_{image_hash}.jpg"

                    saved_image_path = fs.save(product_image_upload_path(product_model.model_number, image_file_name), image)
                    # Create the ProductImage object, saving the path returned by FileSystemStorage
                    ProductImage.objects.create(
                        product_model=product_model,
                        image=saved_image_path,
                        hash=image_hash
                    )
                    print(f"Save image {image_file_name}.")                
            # Handle deletion of existing images if requested
            image_ids_to_delete = request.POST.getlist('delete_images')
            if image_ids_to_delete:
                fs = FileSystemStorage()  # Initialize FileSystemStorage here to avoid UnboundLocalError
                for img_id in image_ids_to_delete:
                    try:
                        img = ProductImage.objects.get(pk=img_id)

                        # Check if the file exists before attempting to delete
                        if img.image and os.path.isfile(img.image.path):
                            fs.delete(img.image.path)  # Delete the image file from storage

                        # Delete the database entry
                        img.delete()
                    except ProductImage.DoesNotExist:
                        print(f"Image with id {img_id} does not exist.")

            # Update existing specifications
            spec_ids = request.POST.getlist('spec_ids')
            spec_values = request.POST.getlist('spec_values')

            for spec_id, value in zip(spec_ids, spec_values):
                try:
                    product_spec = ProductSpec.objects.get(pk=spec_id)
                    product_spec.value = value
                    product_spec.save()
                except ProductSpec.DoesNotExist:
                    # Handle case where specification does not exist
                    continue

            # Handle adding new specifications
            new_spec_names = request.POST.getlist('new_spec_names')
            new_spec_values = request.POST.getlist('new_spec_values')
            
            for name, value in zip(new_spec_names, new_spec_values):
                if name and value:
                    spec, created = Spec.objects.get_or_create(name=name)
                    ProductSpec.objects.create(product_model=product_model, spec=spec, value=value)
                    print("Spec is Added: " ,new_spec_names,new_spec_values)

            # Handle deletion of specifications
            delete_spec_ids = request.POST.getlist('delete_specs')
            print("Specifications to delete:", delete_spec_ids)
            if delete_spec_ids:
                ProductSpec.objects.filter(pk__in=delete_spec_ids).delete()

            # 5. Redirect to a page that shows the details of the updated ProductModel
            return redirect('product_model_list')
    
    else:
        # 6. If the request is GET, render the form with the current ProductModel instance
        form = ProductModelForm(instance=product_model)

    # 7. Render the 'product_model_edit.html' template with the form
    return render(request, 'product/product_model_form.html', {
        'form': form,
        'product_model': product_model,
        'existing_images': existing_images,
        'edit_mode' : True,
    })

@login_required
def product_model_delete(request, pk):
    product_model = get_object_or_404(ProductModel, pk=pk)
    
    if request.method == 'POST':
        product_model.delete()
        return redirect('product_model_list')  # Redirect after deletion
    
    return render(request, 'product/product_model_confirm_delete.html', {'product_model': product_model})

def scraper_view(request):

    brands = Brand.objects.all()
    categories = Category.objects.all()

    if request.method == 'POST':
        url = request.POST.get('url')
        brand = request.POST.get('brand')
        category = request.POST.get('category')  # Get selected category from dropdown

        try:
            scraper_enter(brand, category, url)
            messages.success(request, 'Scraping completed successfully!')
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
        
        return redirect('scraper')

    return render(request, 'product/scraper.html',{'brands': brands, 'categories': categories})

logger = logging.getLogger(__name__)

@csrf_exempt
def scraper_update_model(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_model_id = data.get('product_model_id')

            # 验证参数是否存在
            if not product_model_id:
                return JsonResponse({'status': 'failed', 'message': 'Missing product_model_id'}, status=400)

            # 获取产品型号实例
            product_model_instance = get_object_or_404(ProductModel, pk=product_model_id)

            # 获取产品链接并调用抓取函数
            url = product_model_instance.link
            if not url:
                return JsonResponse({'status': 'failed', 'message': 'No URL found for this product model'}, status=400)

            # 调用抓取函数
            open_lg_sub_page(product_model_instance, url)

            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return JsonResponse({'status': 'failed', 'message': 'Invalid JSON'}, status=400)
        except ProductModel.DoesNotExist:
            logger.error("ProductModel instance not found.")
            return JsonResponse({'status': 'failed', 'message': 'ProductModel instance not found'}, status=404)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return JsonResponse({'status': 'failed', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'failed', 'message': 'Invalid request method'}, status=400)