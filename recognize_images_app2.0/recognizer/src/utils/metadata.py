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
        """Extract metadata from an image"""
        # Check cache first
        if image_path in self.cache:
            cache_entry = self.cache[image_path]
            if os.path.getmtime(image_path) == cache_entry['mtime']:
                return cache_entry['metadata']
        
        try:
            metadata = {}
            with Image.open(image_path) as img:
                # Basic file info
                metadata['filename'] = os.path.basename(image_path)
                metadata['file_size'] = os.path.getsize(image_path)
                metadata['last_modified'] = datetime.fromtimestamp(
                    os.path.getmtime(image_path)
                ).strftime('%Y-%m-%d %H:%M:%S')
                
                # Image info
                metadata['dimensions'] = img.size
                metadata['format'] = img.format
                metadata['mode'] = img.mode
                
                # EXIF data
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    metadata['exif'] = {}
                    for tag_id in exif:
                        tag = TAGS.get(tag_id, tag_id)
                        data = exif[tag_id]
                        # Convert bytes to string
                        if isinstance(data, bytes):
                            data = data.decode(errors='replace')
                        metadata['exif'][tag] = str(data)
            
            # Update cache
            self.cache[image_path] = {
                'mtime': os.path.getmtime(image_path),
                'metadata': metadata
            }
            self._save_cache()
            
            return metadata
        except Exception as e:
            print(f"Error extracting metadata: {str(e)}")
            return None
    
    def _load_cache(self):
        """Load metadata cache from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _save_cache(self):
        """Save metadata cache to file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"Error saving metadata cache: {str(e)}")
    
    def clear_cache(self):
        """Clear the metadata cache"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
