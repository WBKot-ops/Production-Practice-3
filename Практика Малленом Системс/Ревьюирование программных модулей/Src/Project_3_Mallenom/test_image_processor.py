import unittest
import os
from PIL import Image
from project_3_app import ImageProcessor

class TestImageProcessor(unittest.TestCase):
    """Модульные тесты для класса ImageProcessor."""

    def setUp(self):
        """Подготовка тестового изображения."""
        self.test_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_temp_img.png")
        self.img_width = 200
        self.img_height = 100
        self.img = Image.new("RGB", (self.img_width, self.img_height), color="blue")
        self.img.save(self.test_filename)

    def tearDown(self):
        """Очистка за собой."""
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def test_01_get_info_success(self):
        """1. Проверка правильности чтения метаданных изображения."""
        info = ImageProcessor.get_info(self.test_filename)
        self.assertEqual(info["width"], self.img_width)
        self.assertEqual(info["height"], self.img_height)
        self.assertEqual(info["format"], "PNG")

    def test_02_get_info_file_not_found(self):
        """2. Проверка генерации исключения для несуществующего файла."""
        with self.assertRaises(FileNotFoundError):
            ImageProcessor.get_info("non_existing_file_999.png")

    def test_03_convert_to_grayscale(self):
        """3. Проверка преобразования цвета в оттенки серого."""
        gray_img = ImageProcessor.convert_to_grayscale(self.img)
        self.assertIsNotNone(gray_img)
        self.assertEqual(gray_img.size, (self.img_width, self.img_height))

    def test_04_crop_image(self):
        """4. Проверка кадрирования (обрезки)."""
        crop_box = (10, 10, 60, 50)
        cropped_img = ImageProcessor.crop(self.img, crop_box)
        self.assertEqual(cropped_img.width, 50)
        self.assertEqual(cropped_img.height, 40)

    def test_05_resize_image(self):
        """5. Проверка масштабирования."""
        new_w, new_h = 400, 300
        resized_img = ImageProcessor.resize(self.img, new_w, new_h)
        self.assertEqual(resized_img.width, new_w)
        self.assertEqual(resized_img.height, new_h)

if __name__ == "__main__":
    unittest.main()