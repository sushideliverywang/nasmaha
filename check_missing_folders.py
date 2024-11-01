import os
from django.db import connection
import os
import django

# 设置 Django 的 settings 模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nasmaha.settings')
django.setup()


# 假设 MEDIA_ROOT 是存储图片的根目录
MEDIA_ROOT = '/users/yiqunwang/project/nasmaha/media'
product_images_folder = os.path.join(MEDIA_ROOT, 'product_model_images')

# 获取 product_model_images 目录下所有子文件夹名称，并全部转换为小写
folder_names = [name.lower() for name in os.listdir(product_images_folder) if os.path.isdir(os.path.join(product_images_folder, name))]

# 从数据库中获取所有的产品型号，并全部转换为小写
query = "SELECT model_number FROM nasmaha.product_productmodel"
with connection.cursor() as cursor:
    cursor.execute(query)
    model_numbers = [row[0].lower() for row in cursor.fetchall()]

# 找出数据库中有但文件夹中没有的型号（缺少的文件夹）
missing_folders = [model for model in model_numbers if model not in folder_names]

# 找出文件夹中有但数据库中没有的型号（多余的文件夹）
extra_folders = [folder for folder in folder_names if folder not in model_numbers]

# 打印缺少的和多余的文件夹
if missing_folders:
    print("Missing folders for product models:")
    for model in missing_folders:
        print(model)
else:
    print("No missing folders found.")

if extra_folders:
    print("Extra folders found in the file system:")
    for folder in extra_folders:
        print(folder)
else:
    print("No extra folders found.")
