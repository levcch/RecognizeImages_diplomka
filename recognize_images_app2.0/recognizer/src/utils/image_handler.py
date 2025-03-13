from PIL import Image
import os
from pathlib import Path
import shutil

class ImageHandler:
    def __init__(self, base_path):
        self.base_path = base_path
        self.thumbnail_size = (200, 200)
    
    def create_thumbnail(self, image_path):
        """Create a thumbnail for the given image"""
        try:
            with Image.open(image_path) as img:
                img.thumbnail(self.thumbnail_size)
                thumbnail_path = self._get_thumbnail_path(image_path)
                img.save(thumbnail_path)
                return thumbnail_path
        except Exception as e:
            print(f"Error creating thumbnail: {str(e)}")
            return None
    
    def move_image(self, source_path, dest_path):
        """Move an image from source to destination"""
        try:
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Move the image
            shutil.move(source_path, dest_path)
            
            # Move the thumbnail if it exists
            source_thumb = self._get_thumbnail_path(source_path)
            dest_thumb = self._get_thumbnail_path(dest_path)
            if os.path.exists(source_thumb):
                os.makedirs(os.path.dirname(dest_thumb), exist_ok=True)
                shutil.move(source_thumb, dest_thumb)
            
            return True
        except Exception as e:
            print(f"Error moving image: {str(e)}")
            return False
    
    def delete_image(self, image_path):
        """Delete an image and its thumbnail"""
        try:
            # Delete the image
            if os.path.exists(image_path):
                os.remove(image_path)
            
            # Delete the thumbnail
            thumb_path = self._get_thumbnail_path(image_path)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            
            return True
        except Exception as e:
            print(f"Error deleting image: {str(e)}")
            return False
    
    def _get_thumbnail_path(self, image_path):
        """Get the thumbnail path for an image"""
        image_name = Path(image_path).name
        return os.path.join(self.base_path, 'assets', 'thumbnails', image_name)
    
    def get_image_info(self, image_path):
        """Get basic information about an image"""
        try:
            with Image.open(image_path) as img:
                return {
                    'size': os.path.getsize(image_path),
                    'dimensions': img.size,
                    'format': img.format,
                    'mode': img.mode
                }
        except Exception as e:
            print(f"Error getting image info: {str(e)}")
            return None
