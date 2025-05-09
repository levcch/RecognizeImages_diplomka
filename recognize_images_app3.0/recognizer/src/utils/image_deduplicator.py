from PIL import Image
import os
import hashlib
import numpy as np
from pathlib import Path
import imagehash
import shutil

class ImageDeduplicator:
    def __init__(self, file_manager):
        self.file_manager = file_manager
        self.base_path = file_manager.base_path
    
    def find_and_move_duplicates(self, paths=None):
        """
        Поиск дубликатов изображений и перемещение их в корзину
        
        Args:
            paths: Список путей для поиска дубликатов. Если None, поиск во всех папках.
        
        Returns:
            Словарь с информацией о процессе: {
                'total_processed': количество обработанных изображений,
                'duplicates_found': количество найденных дубликатов,
                'space_saved': байт, сэкономленных удалением дубликатов
            }
        """
        if paths is None:
            # Пути по умолчанию для поиска: ai_folders и manual_folders
            paths = [
                os.path.join(self.base_path, 'assets', 'ai_folders'),
                os.path.join(self.base_path, 'assets', 'manual_folders')
            ]
        
        # Сбор всех файлов изображений из указанных путей
        image_files = []
        for path in paths:
            for root, _, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self._is_image(file_path):
                        image_files.append(file_path)
        
        # Поиск дубликатов с использованием комбинации методов
        duplicates = self._find_duplicates(image_files)
        
        # Перемещение дубликатов в корзину
        total_size_saved = 0
        moved_count = 0
        duplicates_report = []
        
        for original, dupes in duplicates.items():
            for dupe in dupes:
                # Расчет размера перед удалением
                file_size = os.path.getsize(dupe)
                total_size_saved += file_size
                
                # Получение относительного пути для file_manager
                rel_path = os.path.relpath(dupe, self.base_path)
                
                # Сохранение информации об этом дубликате
                duplicates_report.append({
                    "original": os.path.relpath(original, self.base_path),
                    "duplicate": rel_path,
                    "size": file_size
                })
                
                # Перемещение в корзину
                print(f"Перемещение дубликата в корзину: {dupe} (оригинал: {original})")
                if self.file_manager.move_to_trash(rel_path):
                    moved_count += 1
        
        return {
            'total_processed': len(image_files),
            'duplicates_found': moved_count,
            'space_saved': total_size_saved,
            'duplicates': duplicates_report
        }
    
    def _is_image(self, path):
        """Проверка, является ли файл изображением"""
        return Path(path).suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']
    
    def _find_duplicates(self, image_files):
        """
        Поиск дубликатов изображений с использованием нескольких методов
        
        Args:
            image_files: Список путей к файлам изображений
        
        Returns:
            Словарь с оригинальным изображением в качестве ключа и списком дубликатов в качестве значения
        """
        # Первый проход: группировка по размеру файла
        size_groups = {}
        for img_path in image_files:
            size = os.path.getsize(img_path)
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(img_path)
        
        # Второй проход: для каждой группы размеров вычисляем хеши изображений
        duplicates = {}
        
        for size, files in size_groups.items():
            if len(files) < 2:  # Пропуск групп с только одним файлом
                continue
            
            # Вычисление перцептивных хешей для всех файлов в этой группе размеров
            hash_dict = {}
            for img_path in files:
                try:
                    img_hash = self._compute_image_hash(img_path)
                    if img_hash not in hash_dict:
                        hash_dict[img_hash] = []
                    hash_dict[img_hash].append(img_path)
                except Exception as e:
                    print(f"Ошибка обработки {img_path}: {str(e)}")
            
            # Поиск дубликатов в группах хешей
            for hash_val, hash_files in hash_dict.items():
                if len(hash_files) > 1:
                    # Используем первый файл как оригинал
                    original = hash_files[0]
                    if original not in duplicates:
                        duplicates[original] = []
                    duplicates[original].extend(hash_files[1:])
        
        return duplicates
    
    def _compute_image_hash(self, img_path):
        """
        Вычисление перцептивного хеша для изображения
        
        Args:
            img_path: Путь к файлу изображения
            
        Returns:
            Строковое представление хеша
        """
        try:
            with Image.open(img_path) as img:
                # Использование комбинации различных методов хеширования для лучшей точности
                phash = imagehash.phash(img)
                dhash = imagehash.dhash(img)
                whash = imagehash.whash(img)
                
                # Объединение хешей для более надежного отпечатка
                combined_hash = str(phash) + str(dhash) + str(whash)
                return combined_hash
        except Exception as e:
            print(f"Ошибка вычисления хеша для {img_path}: {str(e)}")
            # Запасной вариант для хеша файла, если изображение не может быть обработано
            return self._compute_file_hash(img_path)
    
    def _compute_file_hash(self, file_path):
        """
        Вычисление хеша файла с использованием MD5
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Шестнадцатеричное строковое представление хеша
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest() 