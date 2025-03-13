// Global state
let currentPath = '';
let selectedItems = new Set();

// DOM Elements
const folderTree = document.getElementById('folder-tree');
const contentView = document.getElementById('content-view');
const pathContainer = document.getElementById('path-container');
const metadataModal = document.getElementById('metadata-modal');
const metadataContent = document.getElementById('metadata-content');

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    loadFolderStructure();
    setupModalClose();
});

// Load folder structure
async function loadFolderStructure() {
    try {
        const response = await fetch('/api/folders');
        const data = await response.json();
        renderFolderTree(data);
    } catch (error) {
        console.error('Error loading folder structure:', error);
    }
}

// Render folder tree
function renderFolderTree(structure) {
    const tree = document.createElement('ul');
    tree.className = 'folder-tree';

    // Add root folders
    for (const section in structure) {
        // Проверяем, есть ли у корневой папки подпапки
        const hasChildren = structure[section].children && structure[section].children.length > 0;
        
        // Создаем элемент для корневой папки с возможностью раскрытия
        const sectionItem = createFolderItem(section, {
            ...structure[section],
            // Убедимся, что у корневых папок всегда есть стрелка
            hasArrow: true
        });
        
        tree.appendChild(sectionItem);
    }

    folderTree.innerHTML = '';
    folderTree.appendChild(tree);
}

// Create folder item
function createFolderItem(name, data) {
    const li = document.createElement('li');
    li.className = 'folder-item';

    const nameDiv = document.createElement('div');
    nameDiv.className = 'folder-name';
    
    // Add expand/collapse arrow for folders with children or if hasArrow is true
    const hasChildren = data.children && data.children.length > 0;
    const shouldShowArrow = hasChildren || data.hasArrow;
    
    const arrow = document.createElement('span');
    arrow.className = 'folder-arrow';
    arrow.textContent = shouldShowArrow ? '▶' : ' ';
    arrow.style.marginRight = '5px';
    arrow.style.display = 'inline-block';
    arrow.style.width = '12px';
    arrow.style.cursor = shouldShowArrow ? 'pointer' : 'default';
    nameDiv.appendChild(arrow);
    
    // Add folder icon
    const folderIcon = document.createElement('span');
    folderIcon.textContent = '📁';
    folderIcon.style.marginRight = '5px';
    nameDiv.appendChild(folderIcon);
    
    // Add folder name
    const nameSpan = document.createElement('span');
    nameSpan.textContent = name;
    nameDiv.appendChild(nameSpan);
    
    // Use the path from data if available, otherwise construct it
    const itemPath = data.path || name;
    
    // Click handler for arrow to expand/collapse
    if (shouldShowArrow) {
        arrow.onclick = async (e) => {
            e.stopPropagation();
            const childrenUl = li.querySelector('.folder-children');
            
            if (childrenUl && childrenUl.children.length > 0) {
                // Если у нас уже есть подпапки, просто переключаем их видимость
                const isHidden = childrenUl.style.display === 'none';
                childrenUl.style.display = isHidden ? 'block' : 'none';
                
                // Используем класс для анимации стрелки
                if (isHidden) {
                    arrow.textContent = '▼';
                    arrow.classList.add('expanded');
                } else {
                    arrow.textContent = '▶';
                    arrow.classList.remove('expanded');
                }
            } else {
                // Если подпапок еще нет или они пустые, загружаем их
                const hasSubfolders = await loadSubfolders(itemPath, li);
                
                // Если подпапок нет, просто загружаем содержимое папки
                if (!hasSubfolders) {
                    loadFolderContents(itemPath);
                }
            }
        };
    }
    
    // Click handler for folder name to load contents
    nameDiv.onclick = (e) => {
        if (e.target !== arrow) {
            loadFolderContents(itemPath);
        }
    };

    li.appendChild(nameDiv);

    if (hasChildren) {
        const childrenUl = document.createElement('ul');
        childrenUl.className = 'folder-children';
        childrenUl.style.display = 'none'; // Initially collapsed
        data.children.forEach(child => {
            const childItem = createFolderItem(child.name, child);
            childrenUl.appendChild(childItem);
        });
        li.appendChild(childrenUl);
    }

    return li;
}

// Load folder contents
async function loadFolderContents(path) {
    try {
        console.log('Loading contents for path:', path);
        currentPath = path;
        updatePathBar(path);
        
        // Properly decode the path before sending to server
        const decodedPath = decodeURIComponent(path);
        console.log('Decoded path:', decodedPath);
        
        // Convert path if it's in Russian
        let serverPath = decodedPath;
        if (serverPath.startsWith('Папки ручные/')) {
            serverPath = serverPath.replace('Папки ручные/', 'assets/manual_folders/');
        } else if (serverPath === 'Папки ручные') {
            serverPath = 'assets/manual_folders';
        }
        console.log('Server path:', serverPath);
        
        const encodedPath = encodeURIComponent(serverPath);
        console.log('Encoded path:', encodedPath);
        
        const response = await fetch(`/api/folder/contents?path=${encodedPath}`);
        const data = await response.json();
        
        if (response.ok) {
            console.log('Folder contents:', data);
            console.log('Files found:', data.files.length);
            console.log('Folders found:', data.folders.length);
            if (data.files.length === 0) {
                console.log('Warning: No files found in folder');
            }
            renderContents(data);
        } else {
            console.error('Error loading contents:', data.error);
            alert('Ошибка при загрузке содержимого папки: ' + data.error);
        }
    } catch (error) {
        console.error('Error loading folder contents:', error);
        alert('Ошибка при загрузке содержимого папки');
    }
}

// Render contents
function renderContents(data) {
    console.log('Rendering contents...');
    const grid = document.createElement('div');
    grid.className = 'content-grid';

    // Add folders
    if (data.folders && data.folders.length > 0) {
        console.log('Rendering folders:', data.folders);
        data.folders.forEach(folder => {
            grid.appendChild(createItemCard(folder, true));
        });
    }

    // Add files
    if (data.files && data.files.length > 0) {
        console.log('Rendering files:', data.files);
        data.files.forEach(file => {
            console.log('Creating card for file:', file);
            grid.appendChild(createItemCard(file, false));
        });
    } else {
        console.log('No files to render');
    }

    contentView.innerHTML = '';
    contentView.appendChild(createActionButtons());
    contentView.appendChild(grid);
}

// Create item card
function createItemCard(item, isFolder) {
    const card = document.createElement('div');
    card.className = 'item-card';

    // Add checkbox for items in trash
    if (currentPath.includes('trash') || currentPath.includes('Корзина')) {
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'item-checkbox';
        
        // Ensure the path is in the correct format for trash items
        // Extract just the filename and create a clean path
        const filename = item.name;
        const itemPath = 'assets/trash/' + filename;
        
        console.log('Formatted item path in trash:', itemPath);
        checkbox.onchange = () => toggleItemSelection(itemPath);
        card.appendChild(checkbox);

        // Add restore button
        const restoreBtn = document.createElement('button');
        restoreBtn.className = 'restore-button';
        
        // Создаем изображение для кнопки восстановления
        const restoreImg = document.createElement('img');
        restoreImg.src = '/static/images/icons/restore.png';
        restoreImg.alt = 'Восстановить';
        restoreBtn.appendChild(restoreImg);
        
        restoreBtn.title = 'Восстановить';
        restoreBtn.onclick = () => restoreFromTrash(itemPath);
        card.appendChild(restoreBtn);
    } else if (!isFolder) {
        // Only add checkbox for non-folder items outside trash
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'item-checkbox';
        checkbox.onchange = () => toggleItemSelection(item.path);
        card.appendChild(checkbox);
    }

    // Actions menu
    const actions = document.createElement('div');
    actions.className = 'item-actions';
    
    const toolsMenu = document.createElement('div');
    toolsMenu.className = 'tools-menu';
    
    // Create tools trigger button
    const toolsTrigger = document.createElement('button');
    toolsTrigger.className = 'tools-trigger';

    // Создаем изображение для кнопки инструментов
    const toolsIcon = document.createElement('img');
    toolsIcon.src = '/static/images/icons/tools.png';
    toolsIcon.alt = 'Инструменты';
    toolsIcon.style.width = '100%';
    toolsIcon.style.height = '100%';
    toolsIcon.style.objectFit = 'contain';

    toolsTrigger.appendChild(toolsIcon);
    toolsMenu.appendChild(toolsTrigger);
    
    // Create tools content container
    const toolsContent = document.createElement('div');
    toolsContent.className = 'tools-content';
    
    // Add tool buttons based on item type and location
    const tools = isFolder ? [
        { icon: '/static/images/icons/basket.png', action: () => moveToTrash(item.path), title: 'Удалить' },
        { icon: '/static/images/icons/edit.png', action: () => renameItem(item.path), title: 'Переименовать' }
    ] : [
        { icon: '/static/images/icons/basket.png', action: () => moveToTrash(item.path), title: 'Удалить' },
        { icon: '/static/images/icons/edit.png', action: () => renameItem(item.path), title: 'Переименовать' },
        { icon: '/static/images/icons/move.png', action: () => moveToFolder(item.path), title: 'Переместить' },
        { icon: '/static/images/icons/meta.png', action: () => showMetadata(item.path), title: 'Метаданные' }
    ];

    // Don't show regular tools menu in trash
    if (!currentPath.includes('trash') && !currentPath.includes('Корзина')) {
        tools.forEach(tool => {
            const button = document.createElement('button');
            button.className = 'tool-button';
            
            // Создаем изображение для кнопки инструмента
            const img = document.createElement('img');
            img.src = tool.icon;
            img.alt = tool.title;
            
            button.appendChild(img);
            button.title = tool.title;
            button.onclick = (e) => {
                e.stopPropagation();
                tool.action();
            };
            toolsContent.appendChild(button);
        });
        
        toolsMenu.appendChild(toolsContent);
        actions.appendChild(toolsMenu);
        card.appendChild(actions);
    }

    // Image thumbnail or folder icon
    if (!isFolder) {
        const img = document.createElement('img');
        // Convert path if it's in Russian
        let imagePath = item.path;
        if (imagePath.startsWith('Папки ручные/')) {
            imagePath = imagePath.replace('Папки ручные/', 'assets/manual_folders/');
        } else if (imagePath === 'Папки ручные') {
            imagePath = 'assets/manual_folders';
        }
        
        // Log the image path for debugging
        console.log('Loading image:', imagePath);
        
        // Use the API endpoint for thumbnails
        img.src = `/api/image?path=${encodeURIComponent(imagePath)}`;
        img.alt = item.name;
        img.onerror = (e) => {
            console.error('Error loading image:', e);
            img.src = '/static/images/image-placeholder.svg';
        };
        card.appendChild(img);
    } else {
        const folderIcon = document.createElement('div');
        folderIcon.className = 'folder-icon';
        folderIcon.innerHTML = '<img src="/static/images/folder-icon.svg" alt="Folder" style="width: 64px; height: 64px;">';
        card.appendChild(folderIcon);
        
        // Add double click handler for folders in main container
        if (!currentPath.includes('trash') && !currentPath.includes('Корзина')) {
            card.ondblclick = () => {
                loadFolderContents(item.path);
            };
        }
    }

    // Item name
    const name = document.createElement('div');
    name.className = 'item-name';
    name.textContent = item.name || 'Без имени';
    name.title = item.name || 'Без имени';
    card.appendChild(name);

    return card;
}

// Create action buttons container
function createActionButtons() {
    const container = document.createElement('div');
    container.className = 'action-buttons';

    // Debug output
    console.log('Current path:', currentPath);

    // Check if we're in manual_folders by checking the current path
    const isManualFolder = currentPath.includes('manual_folders') || 
                          currentPath.includes('Папки ручные') ||
                          currentPath === 'Папки ручные';

    console.log('Is manual folder:', isManualFolder);

    if (isManualFolder) {
        const createFolderBtn = document.createElement('button');
        createFolderBtn.className = 'btn btn-primary';
        createFolderBtn.textContent = 'Создать папку';
        createFolderBtn.onclick = createNewFolder;
        container.appendChild(createFolderBtn);

        const uploadBtn = document.createElement('button');
        uploadBtn.className = 'btn btn-primary';
        uploadBtn.textContent = 'Загрузить изображения';
        uploadBtn.onclick = uploadImages;
        container.appendChild(uploadBtn);
        
        // Добавляем кнопку "Начать распознавание"
        const recognizeBtn = document.createElement('button');
        recognizeBtn.className = 'btn btn-success';
        recognizeBtn.textContent = 'Начать распознавание';
        recognizeBtn.onclick = () => {
            // Пока без функционала
            console.log('Начать распознавание');
        };
        container.appendChild(recognizeBtn);

        console.log('Added manual folder buttons');
    }

    if (currentPath.includes('trash') || currentPath.includes('Корзина')) {
        const deleteSelectedBtn = document.createElement('button');
        deleteSelectedBtn.className = 'btn btn-danger';
        deleteSelectedBtn.textContent = 'Удалить выбранное';
        deleteSelectedBtn.onclick = deleteFromTrash;
        container.appendChild(deleteSelectedBtn);

        const emptyTrashBtn = document.createElement('button');
        emptyTrashBtn.className = 'btn btn-danger';
        emptyTrashBtn.textContent = 'Очистить корзину';
        emptyTrashBtn.onclick = emptyTrash;
        container.appendChild(emptyTrashBtn);
    }

    return container;
}

// Create action button
function createActionButton(icon, onClick) {
    const button = document.createElement('button');
    button.className = 'btn';
    button.textContent = icon;
    button.onclick = onClick;
    return button;
}

// Update path bar
function updatePathBar(path) {
    // Decode the path to ensure proper display of Russian characters
    const decodedPath = decodeURIComponent(path);
    pathContainer.innerHTML = '';
    
    // Add root segment
    const rootSegment = document.createElement('span');
    rootSegment.className = 'path-segment';
    rootSegment.textContent = 'Главная';
    rootSegment.onclick = () => loadFolderStructure();
    pathContainer.appendChild(rootSegment);

    // If we have a path, add its segments
    if (decodedPath) {
        const segments = decodedPath.split('/').filter(segment => segment);
        let currentPath = '';
        
        segments.forEach((segment, index) => {
            // Add separator
            const separator = document.createElement('span');
            separator.className = 'path-separator';
            separator.textContent = ' > ';
            pathContainer.appendChild(separator);

            // Add segment
            currentPath += (currentPath ? '/' : '') + segment;
            const segmentSpan = document.createElement('span');
            segmentSpan.className = 'path-segment';
            segmentSpan.textContent = segment;
            segmentSpan.style.cursor = 'pointer';
            const pathForClick = currentPath;
            segmentSpan.onclick = () => loadFolderContents(pathForClick);
            pathContainer.appendChild(segmentSpan);
        });
    }
}

// Toggle item selection
function toggleItemSelection(path) {
    console.log('Toggle selection for path:', path);
    
    if (selectedItems.has(path)) {
        console.log('Removing item from selection:', path);
        selectedItems.delete(path);
    } else {
        console.log('Adding item to selection:', path);
        selectedItems.add(path);
    }
    
    // Log all selected items
    console.log('Currently selected items:', Array.from(selectedItems));
}

// Create new folder
async function createNewFolder() {
    // Create modal window
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    
    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';
    
    // Add close button
    const closeBtn = document.createElement('span');
    closeBtn.className = 'close';
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = () => {
        document.body.removeChild(modal);
    };
    
    // Add title
    const title = document.createElement('h2');
    title.textContent = 'Создание новой папки';
    title.style.marginBottom = '20px';
    
    // Add input field
    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Введите имя папки';
    
    // Add save button
    const saveBtn = document.createElement('button');
    saveBtn.className = 'btn btn-success';
    saveBtn.textContent = 'Создать';
    saveBtn.onclick = async () => {
        const name = input.value.trim();
        if (!name) return;
        
        try {
            // Convert path if it's in Russian
            let path = currentPath;
            console.log('Original path:', path);
            
            // If we're at the root of manual folders
            if (path === 'Папки ручные') {
                path = 'assets/manual_folders';
            } else if (path.startsWith('Папки ручные/')) {
                // If we're in a subfolder of manual folders
                path = path.replace('Папки ручные/', 'assets/manual_folders/');
            }
            
            console.log('Converted path:', path);
            
            const response = await fetch('/api/folder/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path, name })
            });

            console.log('Server response status:', response.status);
            const data = await response.json();
            console.log('Server response:', data);
            
            if (response.ok) {
                console.log('Folder created successfully');
                document.body.removeChild(modal);
                await loadFolderContents(currentPath);
            } else {
                console.error('Error creating folder:', data.error);
                alert('Ошибка при создании папки: ' + (data.error || 'Неизвестная ошибка'));
            }
        } catch (error) {
            console.error('Error creating folder:', error);
            alert('Ошибка при создании папки: ' + error.message);
        }
    };
    
    // Assemble modal
    modalContent.appendChild(closeBtn);
    modalContent.appendChild(title);
    modalContent.appendChild(input);
    modalContent.appendChild(saveBtn);
    modal.appendChild(modalContent);
    
    // Add to document and focus input
    document.body.appendChild(modal);
    input.focus();
}

// Upload images
async function uploadImages() {
    // Create a file input element
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = 'image/*';
    
    // Handle file selection
    input.onchange = async (event) => {
        const files = event.target.files;
        if (!files.length) return;
        
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('path', currentPath);
            
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const data = await response.json();
                    alert(data.error || 'Error uploading file');
                }
            } catch (error) {
                console.error('Error uploading file:', error);
                alert('Error uploading file');
            }
        }
        
        // Refresh the current folder view
        loadFolderContents(currentPath);
    };
    
    // Trigger file selection
    input.click();
}

// Move to trash
async function moveToTrash(path) {
    // Определяем, какие файлы нужно переместить
    let pathsToMove = new Set();
    
    // Если есть выбранные элементы и текущий файл среди них
    if (selectedItems.size > 0 && selectedItems.has(path)) {
        // Перемещаем все выбранные элементы
        pathsToMove = new Set(selectedItems);
    } else {
        // Перемещаем только текущий файл
        pathsToMove.add(path);
    }

    if (!confirm(`Переместить ${pathsToMove.size > 1 ? 'выбранные файлы' : 'файл'} в корзину?`)) return;

    try {
        // Перемещаем каждый файл
        for (const filePath of pathsToMove) {
            const response = await fetch('/api/folder/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath })
            });

            if (!response.ok) {
                console.error('Error moving file to trash:', filePath);
            }
        }

        // Очищаем выбранные элементы
        selectedItems.clear();
        
        // Обновляем содержимое папки
        await loadFolderContents(currentPath);
    } catch (error) {
        console.error('Error moving files to trash:', error);
        alert('Ошибка при перемещении файлов в корзину');
    }
}

// Rename item
async function renameItem(path) {
    // Получаем имя файла из пути
    const fileName = path.split('/').pop();
    
    // Определяем, является ли элемент файлом или папкой
    const isFile = fileName.includes('.');
    
    // Получаем расширение файла, если это файл
    let extension = '';
    let baseName = fileName;
    if (isFile) {
        const parts = fileName.split('.');
        extension = '.' + parts.pop();
        baseName = parts.join('.');
    }
    
    // Создаем модальное окно
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    
    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';
    
    // Создаем кнопку закрытия
    const closeBtn = document.createElement('span');
    closeBtn.className = 'close';
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = () => {
        document.body.removeChild(modal);
    };
    
    // Создаем заголовок
    const title = document.createElement('h2');
    title.textContent = 'Переименовать';
    
    // Создаем поле ввода
    const input = document.createElement('input');
    input.type = 'text';
    input.value = baseName;
    input.placeholder = 'File name';
    
    // Создаем кнопку сохранения
    const saveBtn = document.createElement('button');
    saveBtn.className = 'btn btn-success';
    saveBtn.textContent = 'Сохранить';
    
    saveBtn.onclick = async () => {
        const newBaseName = input.value.trim();
        if (!newBaseName) return;
        
        // Формируем новое имя с расширением, если это файл
        const newName = isFile ? newBaseName + extension : newBaseName;
        
        try {
            const response = await fetch('/api/folder/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_path: path, new_name: newName })
            });
            
            if (response.ok) {
                document.body.removeChild(modal);
                loadFolderContents(currentPath);
            } else {
                const data = await response.json();
                alert('Ошибка при переименовании: ' + (data.error || 'Неизвестная ошибка'));
            }
        } catch (error) {
            console.error('Error renaming item:', error);
            alert('Ошибка при переименовании: ' + error.message);
        }
    };
    
    // Добавляем элементы в модальное окно
    modalContent.appendChild(closeBtn);
    modalContent.appendChild(title);
    modalContent.appendChild(input);
    modalContent.appendChild(saveBtn);
    modal.appendChild(modalContent);
    
    // Добавляем модальное окно в body
    document.body.appendChild(modal);
    
    // Фокусируемся на поле ввода и выделяем текст
    input.focus();
    input.select();
}

// Show metadata
async function showMetadata(path) {
    try {
        console.log('Loading metadata for:', path);
        
        // Показываем индикатор загрузки
        metadataContent.innerHTML = '<div style="text-align: center; padding: 20px;"><p>Загрузка метаданных...</p></div>';
        metadataModal.style.display = 'block';
        
        const response = await fetch(`/api/metadata?path=${encodeURIComponent(path)}`);
        const data = await response.json();
        
        if (!response.ok) {
            metadataContent.innerHTML = `<div style="color: red; text-align: center; padding: 20px;">
                <h2>Ошибка</h2>
                <p>${data.error || 'Не удалось загрузить метаданные'}</p>
            </div>`;
            return;
        }
        
        let content = `<h2 style="text-align: center; margin-bottom: 20px;">Метаданные изображения</h2>`;
        
        // Основная информация
        content += `<div style="margin-bottom: 20px;">
            <h3>Основная информация</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Имя файла:</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">${data.filename || 'Н/Д'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Размер файла:</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">${formatFileSize(data.file_size) || 'Н/Д'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Последнее изменение:</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">${data.last_modified || 'Н/Д'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Размеры:</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">${data.dimensions || 'Н/Д'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Формат:</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">${data.format || 'Н/Д'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Режим:</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">${data.mode || 'Н/Д'}</td>
                </tr>
            </table>
        </div>`;
        
        // EXIF данные, если есть
        if (data.exif && Object.keys(data.exif).length > 0) {
            content += `<div>
                <h3>EXIF данные</h3>
                <table style="width: 100%; border-collapse: collapse;">`;
            
            for (const [key, value] of Object.entries(data.exif)) {
                content += `<tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">${key}:</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">${value}</td>
                </tr>`;
            }
            
            content += `</table></div>`;
        }
        
        metadataContent.innerHTML = content;
    } catch (error) {
        console.error('Error loading metadata:', error);
        metadataContent.innerHTML = `<div style="color: red; text-align: center; padding: 20px;">
            <h2>Ошибка</h2>
            <p>Произошла ошибка при загрузке метаданных: ${error.message}</p>
        </div>`;
    }
}

// Функция для форматирования размера файла
function formatFileSize(size) {
    if (!size) return 'Н/Д';
    
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let i = 0;
    let formattedSize = size;
    
    while (formattedSize >= 1024 && i < units.length - 1) {
        formattedSize /= 1024;
        i++;
    }
    
    return `${formattedSize.toFixed(2)} ${units[i]}`;
}

// Empty trash
async function emptyTrash() {
    // If there are selected items, use the deleteFromTrash function
    if (selectedItems.size > 0) {
        deleteFromTrash();
        return;
    }
    
    if (!confirm('Очистить корзину? Это действие нельзя отменить.')) return;
    try {
        // Получаем список всех файлов в корзине
        const response = await fetch(`/api/folder/contents?path=${encodeURIComponent('assets/trash')}`);
        const data = await response.json();
        
        if (response.ok) {
            console.log('Files in trash:', data.files);
            console.log('Folders in trash:', data.folders);
            
            // Удаляем все файлы и папки
            for (const file of data.files) {
                const serverPath = 'assets/trash/' + file.name;
                console.log('Attempting to delete file:', serverPath);
                
                const deleteResponse = await fetch('/api/trash/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: serverPath })
                });
                
                if (!deleteResponse.ok) {
                    const error = await deleteResponse.json();
                    console.error('Error response:', error);
                    throw new Error(error.error || 'Failed to delete file');
                } else {
                    console.log('Successfully deleted file:', serverPath);
                }
            }
            
            for (const folder of data.folders) {
                const serverPath = 'assets/trash/' + folder.name;
                console.log('Attempting to delete folder:', serverPath);
                
                const deleteResponse = await fetch('/api/trash/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: serverPath })
                });
                
                if (!deleteResponse.ok) {
                    const error = await deleteResponse.json();
                    console.error('Error response:', error);
                    throw new Error(error.error || 'Failed to delete folder');
                } else {
                    console.log('Successfully deleted folder:', serverPath);
                }
            }
            await loadFolderContents(currentPath);
        }
    } catch (error) {
        console.error('Error emptying trash:', error);
        alert('Ошибка при очистке корзины: ' + error.message);
    }
}

// Restore from trash
async function restoreFromTrash(path) {
    try {
        // Get the original path (before the file was moved to trash)
        let originalPath = path;
        if (originalPath.startsWith('assets/trash/')) {
            originalPath = originalPath.replace('assets/trash/', '');
        }
        
        // If the path starts with manual_folders, convert it to the Russian name
        if (originalPath.startsWith('assets/manual_folders/')) {
            originalPath = originalPath.replace('assets/manual_folders/', 'Папки ручные/');
        }
        
        console.log('Restoring from trash, path:', path);
        console.log('Original path:', originalPath);
        
        // Get the target folder path (everything before the last slash)
        const lastSlashIndex = originalPath.lastIndexOf('/');
        let targetFolder = lastSlashIndex !== -1 ? originalPath.substring(0, lastSlashIndex) : 'Папки ручные';
        
        // Convert target folder path for the API
        if (targetFolder.startsWith('Папки ручные')) {
            targetFolder = targetFolder.replace('Папки ручные', 'assets/manual_folders');
        }
        
        console.log('Target folder:', targetFolder);
        
        const response = await fetch('/api/file/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_path: path,
                target_folder: targetFolder
            })
        });

        if (response.ok) {
            await loadFolderContents(currentPath);
        } else {
            const error = await response.json();
            console.error('Error response:', error);
            alert('Ошибка при восстановлении: ' + (error.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error restoring from trash:', error);
        alert('Ошибка при восстановлении из корзины');
    }
}

// Setup modal close
function setupModalClose() {
    const closeBtn = document.querySelector('.close');
    if (closeBtn) {
        closeBtn.onclick = (e) => {
            e.stopPropagation();
            metadataModal.style.display = 'none';
        };
    }

    // Закрытие по клику вне модального окна
    window.addEventListener('click', (event) => {
        if (event.target === metadataModal) {
            metadataModal.style.display = 'none';
        }
    });
    
    // Закрытие по клавише Escape
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && metadataModal.style.display === 'block') {
            metadataModal.style.display = 'none';
        }
    });
}

// Handle file selection from Electron
if (window.electron) {
    window.electron.receive('selected-files', async (files) => {
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('path', currentPath);

            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    loadFolderContents(currentPath);
                }
            } catch (error) {
                console.error('Error uploading file:', error);
            }
        }
    });
}

// Move to folder
async function moveToFolder(path) {
    try {
        const response = await fetch('/api/folders');
        const data = await response.json();
        
        // Create folder selection dialog
        const folders = [];
        
        // Get manual folders section
        const manualFoldersKey = Object.keys(data).find(key => key === 'Папки ручные');
        if (manualFoldersKey && data[manualFoldersKey]) {
            getFolderPaths(data[manualFoldersKey], 'Папки ручные', folders);
        }
        
        if (folders.length === 0) {
            alert('Нет доступных папок для перемещения');
            return;
        }
        
        // Create and show folder selection dialog
        const folderPath = await showFolderSelectionDialog(folders);
        if (!folderPath) return;
        
        // Convert the selected path to the correct format
        let targetPath = folderPath;
        if (targetPath.startsWith('Папки ручные/')) {
            targetPath = targetPath.replace('Папки ручные/', 'assets/manual_folders/');
        } else if (targetPath === 'Папки ручные') {
            targetPath = 'assets/manual_folders';
        }
        
        console.log('Moving file from:', path);
        console.log('Target folder:', targetPath);
        
        // Move file to selected folder
        const moveResponse = await fetch('/api/file/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_path: path,
                target_folder: targetPath
            })
        });
        
        if (moveResponse.ok) {
            await loadFolderContents(currentPath);
        } else {
            const error = await moveResponse.json();
            alert('Ошибка при перемещении файла: ' + (error.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error moving file:', error);
        alert('Ошибка при перемещении файла: ' + error.message);
    }
}

// Helper function to get all folder paths
function getFolderPaths(structure, parentPath, result) {
    if (!structure) return;
    
    if (Array.isArray(structure)) {
        structure.forEach(item => {
            if (item.children) {
                const currentPath = parentPath ? `${parentPath}/${item.name}` : item.name;
                result.push(currentPath);
                getFolderPaths(item.children, currentPath, result);
            }
        });
    }
}

// Show folder selection dialog
function showFolderSelectionDialog(folders) {
    return new Promise((resolve) => {
        // Создаем модальное окно
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'block';
        
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        
        // Создаем кнопку закрытия
        const closeBtn = document.createElement('span');
        closeBtn.className = 'close';
        closeBtn.innerHTML = '&times;';
        closeBtn.onclick = () => {
            document.body.removeChild(modal);
            resolve(null);
        };
        
        // Создаем заголовок
        const title = document.createElement('h2');
        title.textContent = 'Выберите папку';
        
        // Создаем выпадающий список
        const select = document.createElement('select');
        // Используем CSS-класс вместо инлайн-стилей
        
        folders.forEach(folder => {
            const option = document.createElement('option');
            option.value = folder;
            option.textContent = folder;
            select.appendChild(option);
        });
        
        // Создаем кнопку сохранения
        const saveBtn = document.createElement('button');
        saveBtn.className = 'btn btn-success';
        saveBtn.textContent = 'Сохранить';
        saveBtn.onclick = () => {
            document.body.removeChild(modal);
            resolve(select.value);
        };
        
        // Добавляем элементы в модальное окно
        modalContent.appendChild(closeBtn);
        modalContent.appendChild(title);
        modalContent.appendChild(select);
        modalContent.appendChild(saveBtn);
        modal.appendChild(modalContent);
        
        // Добавляем модальное окно в body
        document.body.appendChild(modal);
    });
}

// Delete selected items from trash permanently
async function deleteFromTrash() {
    if (selectedItems.size === 0) {
        alert('Выберите файлы для удаления');
        return;
    }
    
    if (!confirm('Удалить выбранные элементы навсегда? Это действие нельзя отменить.')) {
        return;
    }
    
    try {
        for (const path of selectedItems) {
            console.log('Deleting item from trash:', path);
            
            // Ensure the path starts with assets/trash/ and contains only the filename
            let serverPath;
            
            // Extract just the filename regardless of the path format
            const filename = path.split('/').pop();
            serverPath = 'assets/trash/' + filename;
            
            console.log('Final server path for deletion:', serverPath);
            
            const response = await fetch('/api/trash/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: serverPath })
            });
            
            if (!response.ok) {
                const error = await response.json();
                console.error('Error response:', error);
                throw new Error(error.error || 'Failed to delete file');
            } else {
                console.log('Successfully deleted:', serverPath);
            }
        }
        
        selectedItems.clear();
        await loadFolderContents(currentPath);
    } catch (error) {
        console.error('Error deleting items from trash:', error);
        alert('Ошибка при удалении элементов: ' + error.message);
    }
}

// Load subfolder structure
async function loadSubfolders(parentPath, parentElement) {
    try {
        console.log('Loading subfolders for:', parentPath);
        
        // Получаем содержимое папки
        const response = await fetch(`/api/folder/contents?path=${encodeURIComponent(parentPath)}`);
        const data = await response.json();
        
        if (!response.ok) {
            console.error('Error loading subfolders:', data.error);
            return;
        }
        
        // Создаем список для подпапок, если его еще нет
        let childrenUl = parentElement.querySelector('.folder-children');
        if (!childrenUl) {
            childrenUl = document.createElement('ul');
            childrenUl.className = 'folder-children';
            parentElement.appendChild(childrenUl);
        }
        
        // Очищаем список
        childrenUl.innerHTML = '';
        
        // Добавляем подпапки
        if (data.folders && data.folders.length > 0) {
            data.folders.forEach(folder => {
                const childItem = createFolderItem(folder.name, {
                    path: folder.path,
                    hasArrow: true
                });
                childrenUl.appendChild(childItem);
            });
            
            // Показываем список
            childrenUl.style.display = 'block';
            
            // Обновляем стрелку
            const arrow = parentElement.querySelector('.folder-arrow');
            if (arrow) {
                arrow.textContent = '▼';
                arrow.classList.add('expanded');
            }
            
            return true;
        } else {
            // Если подпапок нет, просто загружаем содержимое
            loadFolderContents(parentPath);
            return false;
        }
    } catch (error) {
        console.error('Error loading subfolders:', error);
        return false;
    }
}