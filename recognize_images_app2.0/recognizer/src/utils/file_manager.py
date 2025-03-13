import os
import shutil
from pathlib import Path
from .image_handler import ImageHandler
from .metadata import MetadataHandler

class FileManager:
    def __init__(self, base_path):
        self.base_path = base_path
        self.image_handler = ImageHandler(base_path)
        self.metadata_handler = MetadataHandler()
        
        # Initialize directory structure
        self.init_directories()
    
    def init_directories(self):
        """Initialize the required directory structure"""
        directories = [
            os.path.join(self.base_path, 'assets', 'thumbnails'),
            os.path.join(self.base_path, 'assets', 'ai_folders'),
            os.path.join(self.base_path, 'assets', 'manual_folders'),
            os.path.join(self.base_path, 'assets', 'trash')
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
        # Create .keep files to preserve empty directories in git
        for directory in directories:
            keep_file = os.path.join(directory, '.keep')
            if not os.path.exists(keep_file):
                with open(keep_file, 'w') as f:
                    f.write('')
    
    def create_folder(self, parent_path, folder_name):
        """Create a new folder"""
        try:
            full_path = os.path.join(self.base_path, parent_path, folder_name)
            os.makedirs(full_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating folder: {str(e)}")
            return False
    
    def rename_item(self, old_path, new_name):
        """Rename a file or folder"""
        try:
            old_full_path = os.path.join(self.base_path, old_path)
            new_full_path = os.path.join(os.path.dirname(old_full_path), new_name)
            os.rename(old_full_path, new_full_path)
            return True
        except Exception as e:
            print(f"Error renaming item: {str(e)}")
            return False
    
    def move_to_trash(self, path):
        """Move an item to trash"""
        try:
            source_path = os.path.join(self.base_path, path)
            trash_path = os.path.join(self.base_path, 'assets', 'trash', os.path.basename(path))
            
            # If it's an image, use image handler
            if os.path.isfile(source_path) and self._is_image(source_path):
                return self.image_handler.move_image(source_path, trash_path)
            
            # Otherwise use standard move
            shutil.move(source_path, trash_path)
            return True
        except Exception as e:
            print(f"Error moving to trash: {str(e)}")
            return False
    
    def restore_from_trash(self, item_name, destination):
        """Restore an item from trash"""
        try:
            trash_path = os.path.join(self.base_path, 'assets', 'trash', item_name)
            dest_path = os.path.join(self.base_path, destination, item_name)
            
            # If it's an image, use image handler
            if os.path.isfile(trash_path) and self._is_image(trash_path):
                return self.image_handler.move_image(trash_path, dest_path)
            
            # Otherwise use standard move
            shutil.move(trash_path, dest_path)
            return True
        except Exception as e:
            print(f"Error restoring from trash: {str(e)}")
            return False
    
    def empty_trash(self, items=None):
        """Empty trash completely or delete specific items"""
        try:
            trash_dir = os.path.join(self.base_path, 'assets', 'trash')
            if items is None:
                # Delete everything in trash
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
                # Delete specific items
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
            print(f"Error emptying trash: {str(e)}")
            return False
    
    def get_item_metadata(self, path):
        """Get metadata for an item"""
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
            print(f"Error getting metadata: {str(e)}")
            return None
    
    def _is_image(self, path):
        """Check if a file is an image"""
        return Path(path).suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']
    
    def _get_dir_size(self, path):
        """Get the total size of a directory"""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
        return total
