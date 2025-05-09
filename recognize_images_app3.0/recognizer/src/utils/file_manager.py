import os
import shutil
from pathlib import Path
from .image_handler import ImageHandler
from .metadata import MetadataHandler
from .image_deduplicator import ImageDeduplicator

class FileManager:
    def __init__(self, base_path):
        self.base_path = base_path
        self.image_handler = ImageHandler(base_path)
        self.metadata_handler = MetadataHandler()
        
        # Инициализация структуры директорий
        self.init_directories()
        
        # Инициализация обнаружителя дубликатов после полной инициализации self
        self.image_deduplicator = ImageDeduplicator(self)
    
    def init_directories(self):
        """Инициализация необходимой структуры директорий"""
        directories = [
            os.path.join(self.base_path, 'assets', 'thumbnails'),
            os.path.join(self.base_path, 'assets', 'ai_folders'),
            os.path.join(self.base_path, 'assets', 'manual_folders'),
            os.path.join(self.base_path, 'assets', 'trash'),
            os.path.join(self.base_path, 'assets', 'temp')
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
        # Создание .keep файлов для сохранения пустых директорий в git
        for directory in directories:
            keep_file = os.path.join(directory, '.keep')
            if not os.path.exists(keep_file):
                with open(keep_file, 'w') as f:
                    f.write('')
    
    def create_folder(self, parent_path, folder_name):
        """Создание новой папки"""
        try:
            full_path = os.path.join(self.base_path, parent_path, folder_name)
            os.makedirs(full_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"Ошибка при создании папки: {str(e)}")
            return False
    
    def rename_item(self, old_path, new_name):
        """Переименование файла или папки"""
        try:
            old_full_path = os.path.join(self.base_path, old_path)
            new_full_path = os.path.join(os.path.dirname(old_full_path), new_name)
            os.rename(old_full_path, new_full_path)
            return True
        except Exception as e:
            print(f"Ошибка при переименовании: {str(e)}")
            return False
    
    def move_to_trash(self, path):
        """Перемещение элемента в корзину"""
        try:
            source_path = os.path.join(self.base_path, path)
            trash_path = os.path.join(self.base_path, 'assets', 'trash', os.path.basename(path))
            
            print(f"Перемещение в корзину: {source_path} -> {trash_path}")
            
            # Если это изображение, используем обработчик изображений
            if os.path.isfile(source_path) and self._is_image(source_path):
                result = self.image_handler.move_image(source_path, trash_path)
                print(f"Результат перемещения изображения: {result}")
                return result
            
            # Иначе используем стандартное перемещение
            shutil.move(source_path, trash_path)
            print(f"Стандартное перемещение выполнено успешно")
            return True
        except Exception as e:
            print(f"Ошибка при перемещении в корзину: {str(e)}")
            return False
    
    def restore_from_trash(self, item_name, destination):
        """Восстановление элемента из корзины"""
        try:
            trash_path = os.path.join(self.base_path, 'assets', 'trash', item_name)
            dest_path = os.path.join(self.base_path, destination, item_name)
            
            # Если это изображение, используем обработчик изображений
            if os.path.isfile(trash_path) and self._is_image(trash_path):
                return self.image_handler.move_image(trash_path, dest_path)
            
            # Иначе используем стандартное перемещение
            shutil.move(trash_path, dest_path)
            return True
        except Exception as e:
            print(f"Ошибка при восстановлении из корзины: {str(e)}")
            return False
    
    def empty_trash(self, items=None):
        """Очистка корзины полностью или удаление конкретных элементов"""
        try:
            trash_dir = os.path.join(self.base_path, 'assets', 'trash')
            if items is None:
                # Удаление всего из корзины
                for item in os.listdir(trash_dir):
                    item_path = os.path.join(trash_dir, item)
                    if os.path.isfile(item_path):
                        if self._is_image(item_path):
                            self.image_handler.delete_image(item_path)
                        else:
                            os.remove(item_path)
                    else:
                        shutil.rmtree(item_path)
            else:
                # Удаление конкретных элементов
                for item in items:
                    item_path = os.path.join(trash_dir, item)
                    if os.path.exists(item_path):
                        if os.path.isfile(item_path) and self._is_image(item_path):
                            self.image_handler.delete_image(item_path)
                        elif os.path.isfile(item_path):
                            os.remove(item_path)
                        else:
                            shutil.rmtree(item_path)
            return True
        except Exception as e:
            print(f"Ошибка при очистке корзины: {str(e)}")
            return False
    
    def get_item_metadata(self, path):
        """Получение метаданных для элемента"""
        try:
            full_path = os.path.join(self.base_path, path)
            if os.path.isfile(full_path) and self._is_image(full_path):
                return self.metadata_handler.get_metadata(full_path)
            else:
                return {
                    'name': os.path.basename(full_path),
                    'type': 'folder' if os.path.isdir(full_path) else 'file',
                    'size': self._get_dir_size(full_path) if os.path.isdir(full_path) else os.path.getsize(full_path),
                    'modified': os.path.getmtime(full_path)
                }
        except Exception as e:
            print(f"Ошибка при получении метаданных: {str(e)}")
            return None
    
    def _is_image(self, path):
        """Проверка, является ли файл изображением"""
        return Path(path).suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']
    
    def _get_dir_size(self, path):
        """Получение общего размера директории"""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
        return total
    
    def find_duplicate_images(self, paths=None):
        """Поиск и перемещение дубликатов изображений в корзину"""
        return self.image_deduplicator.find_and_move_duplicates(paths) 