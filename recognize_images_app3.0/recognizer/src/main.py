from flask import Flask, jsonify, request, send_file, render_template
import os
import json
from pathlib import Path
from werkzeug.utils import secure_filename
from PIL import Image
import sys
from utils.file_manager import FileManager
from utils.metadata import MetadataHandler
import urllib.parse
import shutil
import logging
from utils.image_classifier import ImageClassifier

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = Flask(__name__, 
    template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates')),
    static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
)

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'assets', 'thumbnails')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Folder names in Russian
FOLDER_NAMES = {
    'ai_folders': 'Папки ИИ',
    'manual_folders': 'Папки ручные',
    'trash': 'Корзина'
}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize managers
file_manager = FileManager(BASE_DIR)
metadata_handler = MetadataHandler()
image_classifier = ImageClassifier(BASE_DIR)

def allowed_file(filename):
    """Check if file has an allowed extension"""
    if not filename:
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/folders', methods=['GET'])
def get_folders():
    """Get the folder structure"""
    try:
        folder_structure = {
            FOLDER_NAMES['ai_folders']: get_directory_structure(os.path.join(BASE_DIR, 'assets', 'ai_folders')),
            FOLDER_NAMES['manual_folders']: get_directory_structure(os.path.join(BASE_DIR, 'assets', 'manual_folders')),
            FOLDER_NAMES['trash']: get_directory_structure(os.path.join(BASE_DIR, 'assets', 'trash'))
        }
        return jsonify(folder_structure)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/folder/create', methods=['POST'])
def create_folder():
    """Create a new folder"""
    try:
        data = request.get_json()
        path = data.get('path')
        name = data.get('name')
        
        print(f"Received request to create folder - Path: {path}, Name: {name}")
        
        if not path or not name:
            return jsonify({'error': 'Необходимо указать путь и имя папки'}), 400
        
        # Convert path if it contains Russian folder names
        original_path = path
        for key, value in FOLDER_NAMES.items():
            if value in path:
                path = path.replace(value, f'assets/{key}')
        
        print(f"Path after conversion: {path}")
        
        # Ensure the path is within manual_folders
        if 'assets/manual_folders' not in path:
            print(f"Invalid path - not in manual_folders: {path}")
            return jsonify({'error': 'Папки можно создавать только в разделе "Папки ручные"'}), 400
        
        # Create full path and validate it
        full_path = os.path.abspath(os.path.join(BASE_DIR, path, secure_filename(name)))
        base_path = os.path.abspath(BASE_DIR)
        
        print(f"Full path: {full_path}")
        print(f"Base path: {base_path}")
        
        # Ensure the path is within the base directory
        if not full_path.startswith(base_path):
            print(f"Invalid path - outside base directory: {full_path}")
            return jsonify({'error': 'Недопустимый путь'}), 400
        
        # Create the folder
        print(f"Creating folder at: {full_path}")
        os.makedirs(full_path, exist_ok=True)
        
        print("Folder created successfully")
        return jsonify({'message': 'Папка успешно создана'})
    except Exception as e:
        print(f"Error in create_folder: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/folder/rename', methods=['POST'])
def rename_folder():
    """Rename a folder"""
    data = request.get_json()
    old_path = data.get('old_path')
    new_name = data.get('new_name')
    
    if not old_path or not new_name:
        return jsonify({'error': 'Old path and new name are required'}), 400
    
    try:
        old_path = os.path.join(BASE_DIR, old_path)
        new_path = os.path.join(os.path.dirname(old_path), secure_filename(new_name))
        os.rename(old_path, new_path)
        return jsonify({'message': 'Folder renamed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/folder/delete', methods=['POST'])
def delete_folder():
    """Move folder to trash"""
    data = request.get_json()
    path = data.get('path')
    
    if not path:
        return jsonify({'error': 'Path is required'}), 400
    
    try:
        source_path = os.path.join(BASE_DIR, path)
        trash_path = os.path.join(BASE_DIR, 'assets', 'trash', os.path.basename(path))
        os.rename(source_path, trash_path)
        return jsonify({'message': 'Folder moved to trash successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/folder/contents', methods=['GET'])
def get_folder_contents():
    """Get contents of a specific folder"""
    try:
        path = request.args.get('path', '')
        if not path:
            return jsonify({'error': 'Path is required'}), 400

        # Print debug information
        print(f"Original path: {path}")
        
        try:
            # Try UTF-8 first
            path = urllib.parse.unquote(path)
        except Exception as e:
            print(f"Error decoding path with UTF-8: {str(e)}")
            try:
                # Fallback to latin1
                path = path.encode('latin1').decode('utf-8')
            except Exception as e:
                print(f"Error decoding path with latin1: {str(e)}")
                return jsonify({'error': 'Invalid path encoding'}), 400

        print(f"Decoded path: {path}")
        
        # Convert path to use correct folder names
        for key, value in FOLDER_NAMES.items():
            if value in path:
                path = path.replace(value, f'assets/{key}')
        
        print(f"Converted path: {path}")
        
        full_path = os.path.join(BASE_DIR, path)
        print(f"Full path: {full_path}")
        
        # Ensure the path is within the base directory
        if not os.path.abspath(full_path).startswith(os.path.abspath(BASE_DIR)):
            return jsonify({'error': 'Invalid path'}), 400
            
        if not os.path.exists(full_path):
            return jsonify({'error': 'Path does not exist'}), 404
            
        contents = {
            'folders': [],
            'files': []
        }
        
        for item in os.listdir(full_path):
            if item.startswith('.'):  # Skip hidden files
                continue
                
            item_path = os.path.join(full_path, item)
            rel_path = os.path.relpath(item_path, BASE_DIR)
            
            if os.path.isdir(item_path):
                contents['folders'].append({
                    'name': item,
                    'path': rel_path.replace('\\', '/')  # Ensure forward slashes
                })
            elif os.path.isfile(item_path) and allowed_file(item):
                contents['files'].append({
                    'name': item,
                    'path': rel_path.replace('\\', '/'),  # Ensure forward slashes
                    'size': os.path.getsize(item_path)
                })
        
        return jsonify(contents)
    except Exception as e:
        print(f"Error in get_folder_contents: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload a file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    path = request.form.get('path')
    
    if not file or not path:
        return jsonify({'error': 'File and path are required'}), 400
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        # Convert path to use correct folder names
        for key, value in FOLDER_NAMES.items():
            if value in path:
                path = path.replace(value, f'assets/{key}')
        
        # Ensure the path is within manual_folders
        if 'assets/manual_folders' not in path:
            return jsonify({'error': 'Files can only be uploaded to manual folders'}), 400
        
        full_path = os.path.join(BASE_DIR, path)
        # Ensure the path is within the base directory
        if not os.path.abspath(full_path).startswith(os.path.abspath(BASE_DIR)):
            return jsonify({'error': 'Invalid path'}), 400
            
        if not os.path.exists(full_path):
            return jsonify({'error': 'Path does not exist'}), 404
            
        filename = secure_filename(file.filename)
        file_path = os.path.join(full_path, filename)
        
        # First save to a temporary location instead of the target path
        temp_dir = os.path.join(BASE_DIR, 'assets', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)
        
        # Create thumbnail for the temporary file
        with Image.open(temp_path) as img:
            img.thumbnail((200, 200))
            thumb_path = os.path.join(UPLOAD_FOLDER, filename)
            img.save(thumb_path)
        
        # Check if this is a duplicate of existing images
        # Get search paths for duplicate check - all image folders except trash
        search_paths = [
            os.path.join(BASE_DIR, 'assets', 'ai_folders'),
            os.path.join(BASE_DIR, 'assets', 'manual_folders')
        ]
        
        # Collect all existing images to compare against
        all_images = []
        for search_path in search_paths:
            for root, _, files in os.walk(search_path):
                for file_name in files:
                    img_path = os.path.join(root, file_name)
                    if file_manager.image_deduplicator._is_image(img_path):
                        all_images.append(img_path)
        
        # Create a one-to-many comparison
        found_duplicate = False
        duplicate_of = None
        
        for existing_img in all_images:
            try:
                # Compare file size as quick check
                if os.path.getsize(existing_img) == os.path.getsize(temp_path):
                    # Compare hashes
                    new_hash = file_manager.image_deduplicator._compute_image_hash(temp_path)
                    existing_hash = file_manager.image_deduplicator._compute_image_hash(existing_img)
                    
                    if new_hash == existing_hash:
                        # This is a duplicate
                        found_duplicate = True
                        duplicate_of = existing_img
                        break
            except Exception as e:
                print(f"Error comparing images: {str(e)}")
                # Continue with next image if one comparison fails
                continue
        
        if found_duplicate and duplicate_of is not None:
            # File is a duplicate - move it directly to trash
            trash_path = os.path.join(BASE_DIR, 'assets', 'trash', filename)
            
            print(f"Found duplicate - Moving to trash: {temp_path} -> {trash_path}")
            
            # Use shutil.move directly instead of file_manager to avoid complications
            try:
                # Ensure trash directory exists
                os.makedirs(os.path.join(BASE_DIR, 'assets', 'trash'), exist_ok=True)
                
                # Move the temp file to trash
                shutil.move(temp_path, trash_path)
                
                # Return response about duplicate
                return jsonify({
                    'message': 'Файл определен как дубликат и перемещен в корзину',
                    'status': 'duplicate',
                    'original_file': os.path.relpath(duplicate_of, BASE_DIR)
                })
            except Exception as e:
                print(f"Error moving duplicate to trash: {str(e)}")
                # If there was an error moving to trash, at least try to cleanup
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return jsonify({'error': f'Error handling duplicate: {str(e)}'}), 500
        else:
            # No duplicate found, move from temp to actual destination
            try:
                shutil.move(temp_path, file_path)
                return jsonify({'message': 'Файл успешно загружен'})
            except Exception as e:
                print(f"Error moving from temp to destination: {str(e)}")
                return jsonify({'error': str(e)}), 500
                
    except Exception as e:
        print(f"Error in upload_file: {str(e)}")
        # Cleanup any temp files that might have been created
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass
        return jsonify({'error': str(e)}), 500

@app.route('/api/file/move', methods=['POST'])
def move_file():
    """Move file to another folder"""
    data = request.get_json()
    source_path = data.get('source_path')
    target_folder = data.get('target_folder')
    
    if not source_path or not target_folder:
        return jsonify({'error': 'Source path and target folder are required'}), 400
    
    try:
        # Convert paths to use correct folder names
        for key, value in FOLDER_NAMES.items():
            if value in target_folder:
                target_folder = target_folder.replace(value, f'assets/{key}')
        
        source_path = os.path.join(BASE_DIR, source_path)
        target_path = os.path.join(BASE_DIR, target_folder, os.path.basename(source_path))
        
        # Ensure both paths are within the base directory
        if not (os.path.abspath(source_path).startswith(os.path.abspath(BASE_DIR)) and
                os.path.abspath(target_path).startswith(os.path.abspath(BASE_DIR))):
            return jsonify({'error': 'Invalid path'}), 400
        
        # Ensure source file exists
        if not os.path.exists(source_path):
            return jsonify({'error': 'Source file does not exist'}), 404
        
        # Ensure target directory exists
        target_dir = os.path.dirname(target_path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        
        # Move the file
        os.rename(source_path, target_path)
        
        return jsonify({'message': 'File moved successfully'})
    except Exception as e:
        print(f"Error in move_file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/image')
def get_image():
    """Get image file"""
    try:
        path = request.args.get('path', '')
        if not path:
            return jsonify({'error': 'Path is required'}), 400
            
        # Decode the path
        path = urllib.parse.unquote(path)
        
        # Convert path if it contains Russian folder names
        for key, value in FOLDER_NAMES.items():
            if value in path:
                path = path.replace(value, f'assets/{key}')
                
        # Get full path
        full_path = os.path.join(BASE_DIR, path)
        
        # Ensure the path is within the base directory
        if not os.path.abspath(full_path).startswith(os.path.abspath(BASE_DIR)):
            return jsonify({'error': 'Invalid path'}), 400
            
        if not os.path.exists(full_path):
            return jsonify({'error': 'File not found'}), 404
            
        return send_file(full_path)
    except Exception as e:
        print(f"Error in get_image: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trash/delete', methods=['POST'])
def delete_from_trash():
    """Permanently delete file from trash"""
    data = request.get_json()
    path = data.get('path')
    
    if not path:
        return jsonify({'error': 'Path is required'}), 400
    
    try:
        # Normalize the path to ensure it's in the correct format
        # Extract the filename from the path
        filename = os.path.basename(path)
        normalized_path = os.path.join('assets', 'trash', filename)
        full_path = os.path.join(BASE_DIR, normalized_path)
        
        # Debug output
        print(f"Original path: {path}")
        print(f"Normalized path: {normalized_path}")
        print(f"Full path for deletion: {full_path}")
        print(f"Trash directory: {os.path.join(BASE_DIR, 'assets', 'trash')}")
        
        # Ensure the path is within the trash directory
        trash_dir = os.path.join(BASE_DIR, 'assets', 'trash')
        if not full_path.startswith(trash_dir):
            return jsonify({'error': f'Can only delete files from trash. Path: {path}, Normalized path: {normalized_path}'}), 400
        
        # Delete the file using ImageHandler
        if os.path.exists(full_path):
            if os.path.isfile(full_path):
                # Delete file
                if file_manager.image_handler.delete_image(full_path):
                    return jsonify({'message': 'File deleted successfully'})
                else:
                    return jsonify({'error': 'Failed to delete file'}), 500
            else:
                # Delete directory
                shutil.rmtree(full_path)
                return jsonify({'message': 'Directory deleted successfully'})
        else:
            return jsonify({'error': f'File not found: {full_path}'}), 404
            
    except Exception as e:
        print(f"Error in delete_from_trash: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    """Get metadata for an image"""
    try:
        path = request.args.get('path', '')
        if not path:
            return jsonify({'error': 'Path is required'}), 400
        
        # Decode the path
        try:
            path = urllib.parse.unquote(path)
        except Exception as e:
            print(f"Error decoding path: {str(e)}")
            return jsonify({'error': 'Invalid path encoding'}), 400
        
        # Convert path to use correct folder names
        for key, value in FOLDER_NAMES.items():
            if value in path:
                path = path.replace(value, f'assets/{key}')
        
        full_path = os.path.join(BASE_DIR, path)
        
        # Check if file exists
        if not os.path.exists(full_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Check if file is an image
        if not os.path.isfile(full_path) or not allowed_file(os.path.basename(full_path)):
            return jsonify({'error': 'Not an image file'}), 400
        
        # Get metadata
        metadata = file_manager.get_item_metadata(path)
        if metadata:
            # Convert any non-serializable values to strings
            for key, value in metadata.items():
                if isinstance(value, (tuple, list)):
                    metadata[key] = str(value)
            
            # Format exif data for better readability
            if 'exif' in metadata and metadata['exif']:
                formatted_exif = {}
                for tag, value in metadata['exif'].items():
                    formatted_exif[tag] = value
                metadata['exif'] = formatted_exif
            
            return jsonify(metadata)
        else:
            return jsonify({'error': 'Failed to get metadata'}), 500
        
    except Exception as e:
        print(f"Error in get_metadata: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/deduplicate', methods=['POST'])
def deduplicate_images():
    """Find and move duplicate images to trash"""
    try:
        data = request.get_json()
        paths = data.get('paths', None)
        
        # If paths are provided, convert them to use the correct folder structure
        if paths:
            converted_paths = []
            for path in paths:
                # Convert path if it contains Russian folder names
                for key, value in FOLDER_NAMES.items():
                    if value in path:
                        path = path.replace(value, f'assets/{key}')
                converted_paths.append(os.path.join(BASE_DIR, path))
            result = file_manager.find_duplicate_images(converted_paths)
        else:
            result = file_manager.find_duplicate_images()
        
        # Convert bytes to readable format
        result['space_saved_readable'] = format_bytes(result['space_saved'])
        
        return jsonify(result)
    except Exception as e:
        print(f"Error deduplicating images: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recognize', methods=['POST'])
def recognize_images():
    """Process images using neural network"""
    try:
        logging.info("Начинаем распознавание изображений")
        
        # Выполняем обработку изображений из ручных папок
        result = image_classifier.process_all_manual_images()
        
        if result["success"]:
            return jsonify({
                'success': True,
                'message': f'Обработано и распределено по категориям: {result["processed"]} изображений',
                'count': result["processed"]
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Ошибка при распознавании изображений: ' + str(result.get("error", "Неизвестная ошибка"))
            }), 500
    except Exception as e:
        logging.error(f"Ошибка в recognize_images: {str(e)}")
        return jsonify({'error': str(e)}), 500

def format_bytes(size):
    """Format bytes to readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def get_directory_structure(path):
    """Helper function to get directory structure recursively"""
    structure = []
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                structure.append({
                    'name': item,
                    'path': os.path.relpath(item_path, BASE_DIR),
                    'children': get_directory_structure(item_path)
                })
            elif os.path.isfile(item_path) and allowed_file(item):
                structure.append({
                    'name': item,
                    'path': os.path.relpath(item_path, BASE_DIR),
                    'type': 'file'
                })
        return structure
    except Exception:
        return []

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    file_manager.init_directories()
    app.run(port=port, debug=True, host='127.0.0.1') 