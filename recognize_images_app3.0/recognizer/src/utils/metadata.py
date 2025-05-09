from PIL import Image
from PIL.ExifTags import TAGS
import os
import json
from datetime import datetime

class MetadataHandler:
    def __init__(self):
        self.cache_file = '.metadata_cache.json'
        self.cache = self._load_cache()
    
    def get_metadata(self, image_path):
        """Извлечение метаданных из изображения"""
        # Сначала проверить кеш
        if image_path in self.cache:
            cache_entry = self.cache[image_path]
            if os.path.getmtime(image_path) == cache_entry['mtime']:
                return cache_entry['metadata']
        
        try:
            metadata = {}
            with Image.open(image_path) as img:
                # Основная информация о файле
                metadata['filename'] = os.path.basename(image_path)
                metadata['file_size'] = os.path.getsize(image_path)
                metadata['last_modified'] = datetime.fromtimestamp(
                    os.path.getmtime(image_path)
                ).strftime('%Y-%m-%d %H:%M:%S')
                
                # Информация об изображении
                metadata['dimensions'] = img.size
                metadata['format'] = img.format
                metadata['mode'] = img.mode
                
                # Данные EXIF
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    metadata['exif'] = {}
                    for tag_id in exif:
                        tag = TAGS.get(tag_id, tag_id)
                        data = exif[tag_id]
                        # Преобразовать байты в строку
                        if isinstance(data, bytes):
                            data = data.decode(errors='replace')
                        metadata['exif'][tag] = str(data)
            
            # Обновить кеш
            self.cache[image_path] = {
                'mtime': os.path.getmtime(image_path),
                'metadata': metadata
            }
            self._save_cache()
            
            return metadata
        except Exception as e:
            print(f"Ошибка при извлечении метаданных: {str(e)}")
            return None
    
    def _load_cache(self):
        """Загрузка кеша метаданных из файла"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _save_cache(self):
        """Сохранение кеша метаданных в файл"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"Ошибка при сохранении кеша метаданных: {str(e)}")
    
    def clear_cache(self):
        """Очистка кеша метаданных"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file) 