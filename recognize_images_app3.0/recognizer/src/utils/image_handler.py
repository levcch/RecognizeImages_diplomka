from PIL import Image
import os
from pathlib import Path
import shutil

class ImageHandler:
    def __init__(self, base_path):
        self.base_path = base_path
        self.thumbnail_size = (200, 200)
    
    def create_thumbnail(self, image_path):
        """Создание миниатюры для указанного изображения"""
        try:
            with Image.open(image_path) as img:
                img.thumbnail(self.thumbnail_size)
                thumbnail_path = self._get_thumbnail_path(image_path)
                img.save(thumbnail_path)
                return thumbnail_path
        except Exception as e:
            print(f"Ошибка при создании миниатюры: {str(e)}")
            return None
    
    def move_image(self, source_path, dest_path):
        """Перемещение изображения из источника в пункт назначения"""
        try:
            print(f"ImageHandler перемещает: {source_path} -> {dest_path}")
            
            # Убедиться, что директория назначения существует
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Проверить, существует ли файл
            if not os.path.exists(source_path):
                print(f"Исходный файл не существует: {source_path}")
                return False
            
            # Переместить изображение
            print(f"Перемещение файла изображения")
            shutil.move(source_path, dest_path)
            print(f"Перемещение файла изображения выполнено успешно")
            
            # Переместить миниатюру, если она существует
            source_thumb = self._get_thumbnail_path(source_path)
            dest_thumb = self._get_thumbnail_path(dest_path)
            
            print(f"Проверка наличия миниатюры: {source_thumb}")
            if os.path.exists(source_thumb):
                print(f"Перемещение миниатюры: {source_thumb} -> {dest_thumb}")
                os.makedirs(os.path.dirname(dest_thumb), exist_ok=True)
                shutil.move(source_thumb, dest_thumb)
                print(f"Перемещение миниатюры выполнено успешно")
            else:
                print(f"Миниатюра для перемещения не найдена")
            
            return True
        except Exception as e:
            print(f"Ошибка при перемещении изображения: {str(e)}")
            return False
    
    def delete_image(self, image_path):
        """Удаление изображения и его миниатюры"""
        try:
            # Удалить изображение
            if os.path.exists(image_path):
                os.remove(image_path)
            
            # Удалить миниатюру
            thumb_path = self._get_thumbnail_path(image_path)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            
            return True
        except Exception as e:
            print(f"Ошибка при удалении изображения: {str(e)}")
            return False
    
    def _get_thumbnail_path(self, image_path):
        """Получение пути к миниатюре для изображения"""
        image_name = Path(image_path).name
        return os.path.join(self.base_path, 'assets', 'thumbnails', image_name)
    
    def get_image_info(self, image_path):
        """Получение основной информации об изображении"""
        try:
            with Image.open(image_path) as img:
                return {
                    'size': os.path.getsize(image_path),
                    'dimensions': img.size,
                    'format': img.format,
                    'mode': img.mode
                }
        except Exception as e:
            print(f"Ошибка при получении информации об изображении: {str(e)}")
            return None 