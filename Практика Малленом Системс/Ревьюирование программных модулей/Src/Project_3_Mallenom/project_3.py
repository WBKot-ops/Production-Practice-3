import sys
import os
import json
import logging
from datetime import datetime
from PIL import Image, UnidentifiedImageError, ImageOps

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QSpinBox, QMessageBox,
    QGraphicsView, QGraphicsScene, QRubberBand,
    QFrame, QGroupBox, QSplitter
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QRect, QPoint, QSize

def ensure_directories_exist():
    """Автоматическое создание всех необходимых служебных директорий."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for folder in ["logs", "configs", "output"]:
        dir_path = os.path.join(base_dir, folder)
        os.makedirs(dir_path, exist_ok=True)

ensure_directories_exist()

# Настройка логирования
logging.basicConfig(
    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "app.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


class ImageProcessor:
    """Библиотека обработки изображений."""

    @staticmethod
    def get_info(file_path: str) -> dict:
        """Получение информации о файле."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        try:
            with Image.open(file_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format if img.format else "UNKNOWN",
                    "size_bytes": os.path.getsize(file_path)
                }
        except UnidentifiedImageError:
            raise ValueError("Выбранный файл не является поддерживаемым изображением.")

    @staticmethod
    def convert_to_grayscale(img: Image.Image) -> Image.Image:
        """Преобразование в черно-белый формат (Grayscale)."""
        logging.info("Применение фильтра: Перевод в оттенки серого (ч/б)")
        return ImageOps.grayscale(img).convert("RGB")

    @staticmethod
    def crop(img: Image.Image, box: tuple) -> Image.Image:
        """Обрезка (crop) прямоугольной области: box = (left, upper, right, lower)."""
        logging.info(f"Выполнение обрезки области: {box}")
        return img.crop(box)

    @staticmethod
    def resize(img: Image.Image, width: int, height: int) -> Image.Image:
        """Изменение разрешения / размера изображения."""
        logging.info(f"Изменение разрешения до {width}x{height}")
        return img.resize((width, height), Image.Resampling.LANCZOS)


class AppStateManager:
    """Управление файлами конфигурации и историей действий пользователя."""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_PATH = os.path.join(BASE_DIR, "configs", "settings.json")
    HISTORY_PATH = os.path.join(BASE_DIR, "configs", "history.json")

    @classmethod
    def load_settings(cls) -> dict:
        if os.path.exists(cls.CONFIG_PATH):
            try:
                with open(cls.CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_path": "", "window_size": [1000, 650]}

    @classmethod
    def save_settings(cls, settings: dict):
        with open(cls.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)

    @classmethod
    def append_history(cls, operation: str, details: str):
        history = []
        if os.path.exists(cls.HISTORY_PATH):
            try:
                with open(cls.HISTORY_PATH, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        record = {
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operation": operation,
            "details": details
        }
        history.append(record)

        with open(cls.HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=4)


class ImageAreaWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = None
        self.setAcceptDrops(True)

        self.rubberBand = None
        self.origin = QPoint()
        self.crop_rect_pixels = None

    def set_image(self, pil_img: Image.Image):
        self.scene.clear()
        self.crop_rect_pixels = None
        
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        data = pil_img.tobytes("raw", "RGB")
        qimg = QImage(data, pil_img.width, pil_img.height, pil_img.width * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.setSceneRect(0, 0, pil_img.width, pil_img.height)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap_item:
            self.origin = event.pos()
            if not self.rubberBand:
                self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.rubberBand and self.rubberBand.isVisible():
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.rubberBand and self.rubberBand.isVisible() and self.pixmap_item:
            rect = self.rubberBand.geometry()
            scene_rect = self.mapToScene(rect).boundingRect()
            
            left = max(0, int(scene_rect.left()))
            top = max(0, int(scene_rect.top()))
            right = min(int(self.scene.width()), int(scene_rect.right()))
            bottom = min(int(self.scene.height()), int(scene_rect.bottom()))

            if right > left and bottom > top:
                self.crop_rect_pixels = (left, top, right, bottom)
            else:
                self.crop_rect_pixels = None
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self.window().load_image_from_path(file_path)
                break


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Утилита работы с изображениями, практикант: Никифоров Артём Дмитриевич")
        
        self.settings = AppStateManager.load_settings()
        self.resize(self.settings.get("window_size", [1000, 650])[0], 
                    self.settings.get("window_size", [1000, 650])[1])

        self.current_pil_image = None
        self.previous_pil_image = None
        self.current_file_path = ""

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        
        # Панель инструментов
        btn_box = QGroupBox("Панель инструментов")
        btn_layout = QVBoxLayout(btn_box)

        self.btn_load = QPushButton("Загрузить изображение")
        self.btn_load.clicked.connect(self.on_load_clicked)

        self.btn_crop = QPushButton("Обрезать область")
        self.btn_crop.clicked.connect(self.on_crop_clicked)

        self.btn_grayscale = QPushButton("Преобразовать в ч/б")
        self.btn_grayscale.clicked.connect(self.on_grayscale_clicked)

        self.btn_undo = QPushButton("Отменить (Undo)")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self.on_undo_clicked)

        self.btn_save = QPushButton("Сохранить результат")
        self.btn_save.clicked.connect(self.on_save_clicked)

        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_crop)
        btn_layout.addWidget(self.btn_grayscale)
        btn_layout.addWidget(self.btn_undo)
        btn_layout.addWidget(self.btn_save)

        # Изменение размера
        resize_box = QGroupBox("Изменение разрешения")
        resize_layout = QHBoxLayout(resize_box)
        self.spin_w = QSpinBox()
        self.spin_w.setRange(1, 10000)
        self.spin_h = QSpinBox()
        self.spin_h.setRange(1, 10000)
        btn_resize = QPushButton("Изменить")
        btn_resize.clicked.connect(self.on_resize_clicked)

        resize_layout.addWidget(QLabel("Ш:"))
        resize_layout.addWidget(self.spin_w)
        resize_layout.addWidget(QLabel("В:"))
        resize_layout.addWidget(self.spin_h)
        resize_layout.addWidget(btn_resize)

        # Информация об изображении
        info_box = QGroupBox("Информация об изображении")
        info_layout = QVBoxLayout(info_box)
        self.lbl_info = QLabel("Файл не загружен")
        self.lbl_info.setWordWrap(True)
        info_layout.addWidget(self.lbl_info)

        left_layout.addWidget(btn_box)
        left_layout.addWidget(resize_box)
        left_layout.addWidget(info_box)
        left_layout.addStretch()

        self.image_view = ImageAreaWidget(self)

        splitter.addWidget(left_panel)
        splitter.addWidget(self.image_view)
        splitter.setSizes([300, 700])

    def save_state_for_undo(self):
        if self.current_pil_image:
            self.previous_pil_image = self.current_pil_image.copy()
            self.btn_undo.setEnabled(True)

    def update_image_display(self):
        if self.current_pil_image:
            self.image_view.set_image(self.current_pil_image)
            self.spin_w.setValue(self.current_pil_image.width)
            self.spin_h.setValue(self.current_pil_image.height)

            info_text = (
                f"<b>Файл:</b> {os.path.basename(self.current_file_path)}<br>"
                f"<b>Разрешение:</b> {self.current_pil_image.width} x {self.current_pil_image.height} px<br>"
                f"<b>Цветовой режим:</b> {self.current_pil_image.mode}"
            )
            self.lbl_info.setText(info_text)

    def load_image_from_path(self, path: str):
        try:
            info = ImageProcessor.get_info(path)
            self.current_pil_image = Image.open(path)
            self.current_file_path = path
            self.previous_pil_image = None
            self.btn_undo.setEnabled(False)

            self.update_image_display()

            self.settings["last_path"] = path
            AppStateManager.save_settings(self.settings)
            AppStateManager.append_history("Загрузка файла", path)
            logging.info(f"Успешно загружен файл: {path}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{str(e)}")
            logging.error(f"Ошибка загрузки файла {path}: {str(e)}")

    def on_load_clicked(self):
        last_dir = os.path.dirname(self.settings.get("last_path", ""))
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите изображение", last_dir, "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.load_image_from_path(path)

    def on_crop_clicked(self):
        if not self.current_pil_image:
            return
        box = self.image_view.crop_rect_pixels
        if not box:
            QMessageBox.warning(self, "Предупреждение", "Выделите прямоугольную область мышью на изображении.")
            return

        self.save_state_for_undo()
        self.current_pil_image = ImageProcessor.crop(self.current_pil_image, box)
        self.update_image_display()
        AppStateManager.append_history("Обрезка (Crop)", f"Область: {box}")

    def on_grayscale_clicked(self):
        if not self.current_pil_image:
            return
        self.save_state_for_undo()
        self.current_pil_image = ImageProcessor.convert_to_grayscale(self.current_pil_image)
        self.update_image_display()
        AppStateManager.append_history("Фильтр ч/б", "Конвертация в Grayscale")

    def on_resize_clicked(self):
        if not self.current_pil_image:
            return
        w, h = self.spin_w.value(), self.spin_h.value()
        self.save_state_for_undo()
        self.current_pil_image = ImageProcessor.resize(self.current_pil_image, w, h)
        self.update_image_display()
        AppStateManager.append_history("Изменение разрешения", f"Новый размер: {w}x{h}")

    def on_undo_clicked(self):
        if self.previous_pil_image:
            self.current_pil_image = self.previous_pil_image.copy()
            self.previous_pil_image = None
            self.btn_undo.setEnabled(False)
            self.update_image_display()
            AppStateManager.append_history("Отмена (Undo)", "Возврат к предыдущему состоянию")

    def on_save_clicked(self):
        if not self.current_pil_image:
            return
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_out = os.path.join(base_dir, "output", "result.png")
        save_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Сохранить файл", default_out, "PNG (*.png);;JPEG (*.jpg *.jpeg)"
        )
        if save_path:
            try:
                fmt = "PNG" if ".png" in save_path.lower() else "JPEG"
                self.current_pil_image.save(save_path, fmt)
                QMessageBox.information(self, "Успех", f"Файл успешно сохранен:\n{save_path}")
                AppStateManager.append_history("Сохранение", save_path)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении файла:\n{str(e)}")

    def closeEvent(self, event):
        self.settings["window_size"] = [self.width(), self.height()]
        AppStateManager.save_settings(self.settings)
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())