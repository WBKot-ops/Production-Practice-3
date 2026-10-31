import time
import os
import glob
from PIL import Image, ImageOps

def benchmark_image_operations():

    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    extensions = ('*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.webp')
    image_files = []
    for ext in extensions:
        image_files.extend(glob.glob(os.path.join(base_dir, ext)))
        image_files.extend(glob.glob(os.path.join(base_dir, ext.upper())))
    
    image_files = list(set(image_files))

    if not image_files:
        print(f"[ОШИБКА] В папке {base_dir} не найдено ни одного изображения!")
        print("Пожалуйста, положите любой файл .jpg, .png или .bmp в папку со скриптом.")
        return

    image_path = image_files[0]
    
    output_dir = os.path.join(base_dir, "output")
    original_filename = os.path.basename(image_path)
    name_without_ext, _ = os.path.splitext(original_filename)
    output_path = os.path.join(output_dir, f"{name_without_ext}_result.png")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"--- Замер скорости для файла: {original_filename} ---")
    
    try:
        # 1. Замер загрузки изображения
        start_time = time.perf_counter()
        img = Image.open(image_path)
        img.load() # Принудительно загружаем в память для точного замера
        load_time = time.perf_counter() - start_time
        print(f"1. Загрузка изображения (Open): {load_time * 1000:.2f} мс.")
        print(f"   [Инфо] Разрешение: {img.width}x{img.height}, Формат: {img.format}")

        # 2. Замер Grayscale (Ч/Б)
        start_time = time.perf_counter()
        img_gray = ImageOps.grayscale(img)
        gray_time = time.perf_counter() - start_time
        print(f"2. Преобразование в Ч/Б (Grayscale): {gray_time * 1000:.2f} мс.")

        # 3. Замер Resize (Изменение разрешения до 800x600)
        start_time = time.perf_counter()
        img_resized = img.resize((800, 600), Image.Resampling.LANCZOS)
        resize_time = time.perf_counter() - start_time
        print(f"3. Изменение разрешения (Resize до 800x600): {resize_time * 1000:.2f} мс.")

        # 4. Замер Crop (Обрезка)
        start_time = time.perf_counter()
        width, height = img.size
        crop_size = min(500, width, height)
        left = (width - crop_size) / 2
        top = (height - crop_size) / 2
        right = (width + crop_size) / 2
        bottom = (height + crop_size) / 2
        img_cropped = img.crop((left, top, right, bottom))
        crop_time = time.perf_counter() - start_time
        print(f"4. Обрезка (Crop): {crop_time * 1000:.2f} мс.")

        # 5. Замер сохранения
        start_time = time.perf_counter()
        img_cropped.save(output_path)
        save_time = time.perf_counter() - start_time
        print(f"5. Сохранение результата (Save): {save_time * 1000:.2f} мс.")
        
        print("-" * 40)
        total_time = load_time + gray_time + resize_time + crop_time + save_time
        print(f"Общее время выполнения: {total_time * 1000:.2f} мс.")
        print(f"Результат сохранен в: output/{name_without_ext}_result.png")

    except Exception as e:
        print(f"[ОШИБКА ПРИ ОБРАБОТКЕ] {e}")

if __name__ == "__main__":
    benchmark_image_operations()