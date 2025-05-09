import os
import shutil
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input, decode_predictions
from PIL import Image
import logging

# Словарь для перевода распространенных категорий ImageNet
CATEGORY_TRANSLATIONS = {
    "cat": "Кошка",
    "dog": "Собака",
    "car": "Автомобиль",
    "truck": "Грузовик",
    "airplane": "Самолет",
    "bird": "Птица",
    "flower": "Цветок",
    "tree": "Дерево",
    "house": "Дом",
    "mountain": "Гора",
    "person": "Человек",
    "book": "Книга",
    "chair": "Стул",
    "table": "Стол",
    "computer": "Компьютер",
    "bottle": "Бутылка",
    "food": "Еда",
    "fruit": "Фрукт",
    "water": "Вода",
    "airliner": "Самолет",
    # Можно добавить больше переводов по необходимости
}

class ImageClassifier:
    def __init__(self, base_path):
        self.base_path = base_path
        self.model = None
        self.initialize_model()
        
    def initialize_model(self):
        """Инициализация предобученной модели MobileNetV2"""
        try:
            # Загружаем предобученную модель без верхних слоев классификации
            self.model = MobileNetV2(weights='imagenet', include_top=True)
            logging.info("Модель нейросети успешно инициализирована")
        except Exception as e:
            logging.error(f"Ошибка инициализации модели: {str(e)}")
            self.model = None
    
    def classify_image(self, img_path):
        """Классифицировать одно изображение"""
        try:
            if self.model is None:
                self.initialize_model()
                if self.model is None:
                    return None
                
            # Загрузка и предобработка изображения
            img = Image.open(img_path).convert('RGB')
            img = img.resize((224, 224))
            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = preprocess_input(img_array)
            
            # Предсказание
            predictions = self.model.predict(img_array)
            
            # Получение лучшего класса
            decoded_predictions = decode_predictions(predictions, top=1)[0]
            class_name = decoded_predictions[0][1]
            
            return class_name
        except Exception as e:
            logging.error(f"Ошибка классификации изображения {img_path}: {str(e)}")
            return None
    
    def translate_category(self, category):
        """Переводит категорию на русский язык, если есть в словаре"""
        # Приводим категорию к нижнему регистру для поиска
        category_lower = category.lower()
        
        # Ищем полное совпадение
        if category_lower in CATEGORY_TRANSLATIONS:
            return CATEGORY_TRANSLATIONS[category_lower]
            
        # Ищем частичное совпадение (если категория содержит ключевое слово)
        for eng, rus in CATEGORY_TRANSLATIONS.items():
            if eng in category_lower:
                return rus
                
        # Если перевод не найден, возвращаем оригинальную категорию
        return category
        
    def process_images_batch(self, source_folder, destination_folder):
        """Обработать все изображения из исходной папки и распределить по категориям"""
        try:
            # Создаем основную папку назначения, если ее нет
            os.makedirs(destination_folder, exist_ok=True)
            
            # Счетчик обработанных файлов
            processed_count = 0
            
            # Пройдем по всем файлам в исходной папке и ее подпапках
            for root, _, files in os.walk(source_folder):
                for file in files:
                    # Проверяем, что файл является изображением
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        img_path = os.path.join(root, file)
                        
                        # Классифицируем изображение
                        class_name = self.classify_image(img_path)
                        
                        if class_name:
                            # Переводим категорию на русский, если возможно
                            translated_class = self.translate_category(class_name)
                            
                            # Приводим название класса к виду, подходящему для имени папки
                            folder_name = translated_class.replace(" ", "_")
                            
                            # Создаем папку для категории, если ее нет
                            class_folder = os.path.join(destination_folder, folder_name)
                            os.makedirs(class_folder, exist_ok=True)
                            
                            # Копируем файл в соответствующую папку
                            dest_file_path = os.path.join(class_folder, file)
                            shutil.copy2(img_path, dest_file_path)
                            
                            processed_count += 1
            
            return {
                "success": True,
                "processed": processed_count
            }
        except Exception as e:
            logging.error(f"Ошибка при обработке партии изображений: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_all_manual_images(self):
        """Обработать все изображения из ручных папок и распределить их по категориям в папке ИИ"""
        try:
            manual_folders_path = os.path.join(self.base_path, 'assets', 'manual_folders')
            ai_folders_path = os.path.join(self.base_path, 'assets', 'ai_folders')
            
            result = self.process_images_batch(manual_folders_path, ai_folders_path)
            
            return result
        except Exception as e:
            logging.error(f"Ошибка при обработке всех изображений: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 