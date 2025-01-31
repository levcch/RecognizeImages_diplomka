import os
import shutil
import base64
import dash
from dash import Dash, html, dcc, Input, Output, State, ctx
from flask import Flask

# ------------------------------------------------
# ИНИЦИАЛИЗАЦИЯ
# ------------------------------------------------
server = Flask(__name__, static_folder='static')
app = Dash(__name__, server=server, suppress_callback_exceptions=True)

# Папка, откуда строим дерево (на уровень выше)
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Папка-корзина
TRASH_PATH = os.path.join(os.path.dirname(__file__), "trash")
if not os.path.exists(TRASH_PATH):
    os.makedirs(TRASH_PATH)

# Глобальный словарь: trash_file -> original_file (для восстановления)
TRASH_RECORDS = {}

# ------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ------------------------------------------------
def get_subfolders(folder_path):
    subfolders = []
    try:
        with os.scandir(folder_path) as it:
            for entry in it:
                if entry.is_dir() and not entry.name.startswith('.'):
                    subfolders.append(entry.name)
    except PermissionError:
        pass
    return sorted(subfolders)

def list_images_in_folder(folder_path):
    """Сканируем папку на предмет .png, .jpg, .jpeg, .gif"""
    if not os.path.isdir(folder_path):
        return []
    images = []
    for f in os.listdir(folder_path):
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            images.append(f)
    return images

def generate_tree(folder_path, expanded_folders):
    """Рекурсивное построение дерева папок."""
    subfolders = get_subfolders(folder_path)
    if not subfolders:
        return []
    items = []
    for subf in subfolders:
        full_subf_path = os.path.join(folder_path, subf)
        is_expanded = full_subf_path in expanded_folders
        arrow_symbol = "▼" if is_expanded else "►"

        arrow_id = {'type': 'arrow', 'folder': full_subf_path}
        folder_name_id = {'type': 'folder-name', 'folder': full_subf_path}

        children_div = []
        if is_expanded:
            sub_tree = generate_tree(full_subf_path, expanded_folders)
            if sub_tree:
                children_div = html.Div(sub_tree, style={'marginLeft': '20px'})

        items.append(
            html.Div(
                style={'marginBottom': '5px'},
                children=[
                    html.Span(
                        arrow_symbol,
                        id=arrow_id,
                        style={'cursor': 'pointer', 'marginRight': '5px', 'color': '#ccc'}
                    ),
                    html.Span(
                        "📁 " + subf,
                        id=folder_name_id,
                        style={'cursor': 'pointer'}
                    ),
                    children_div
                ]
            )
        )
    return items

# ------------------------------------------------
# "ЧИСТАЯ" ФУНКЦИЯ: build_thumbnails
# ------------------------------------------------
def build_thumbnails(folder_path, selected_trash_items):
    """
    Возвращает список children (DIV-ы) для 'thumbnails-container',
    в зависимости от того, корзина это или обычная папка.
    """
    if not os.path.isdir(folder_path):
        return []

    images = list_images_in_folder(folder_path)
    children = []

    if folder_path != TRASH_PATH:
        # Обычная папка: выводим миниатюры + иконку "Перейти в корзину"
        for img_name in images:
            full_path = os.path.join(folder_path, img_name)
            encoded = None
            try:
                with open(full_path, 'rb') as f:
                    encoded = base64.b64encode(f.read()).decode('utf-8')
            except:
                pass
            if encoded:
                src = f"data:image/jpeg;base64,{encoded}"
                basket_btn_id = {'type': 'basket-btn', 'file_path': full_path}

                item_div = html.Div(
                    style={
                        'width': '100px',
                        'height': '130px',
                        'border': '1px solid #999',
                        'display': 'flex',
                        'flexDirection': 'column',
                        'alignItems': 'center',
                        'justifyContent': 'space-between',
                        'padding': '5px',
                        'backgroundColor': 'rgba(255,255,255,0.8)',
                        'position': 'relative'
                    },
                    children=[
                        # Иконка удаления
                        html.Div(
                            style={'position': 'absolute', 'top': '3px', 'right': '3px'},
                            children=[
                                html.Img(
                                    src="/static/basket.png",
                                    id=basket_btn_id,
                                    style={'width': '16px', 'cursor': 'pointer'}
                                )
                            ]
                        ),
                        html.Img(
                            src=src,
                            style={'width': '80px', 'height': '80px', 'objectFit': 'cover'}
                        ),
                        html.Div(img_name, style={'fontSize': '10px', 'textAlign': 'center', 'maxWidth': '80px'})
                    ]
                )
                children.append(item_div)

        # Кнопка "Перейти в корзину"
        go_trash_id = {'type': 'folder-name', 'folder': TRASH_PATH}
        go_trash_btn = html.Div(
            style={
                'position': 'absolute',
                'bottom': '10px',
                'right': '10px',
                'cursor': 'pointer'
            },
            children=[
                html.Img(
                    src="/static/basket_folder.png",
                    id=go_trash_id,
                    style={'width': '72px', 'border': 'none', 'borderRadius': '5px'}
                )
            ]
        )
        children.append(go_trash_btn)

        # КНОПКА ЗАГРУЗКИ ФАЙЛОВ (dcc.Upload)
        upload_div = html.Div(
            style={
                'position': 'absolute',
                'bottom': '20px',
                'right': '200px',
                'cursor': 'pointer'
            },
            children=[
                dcc.Upload(
                    id='upload-image',
                    children=html.Div(["Загрузить файлы"]),
                    multiple=True,
                    style={
                        'width': '160px',
                        'height': '40px',
                        'lineHeight': '40px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'backgroundColor': '#fff'
                    }
                )
            ]
        )
        children.append(upload_div)

    else:
        # КОРЗИНА (trash)
        for img_name in images:
            trash_file = os.path.join(folder_path, img_name)
            encoded = None
            try:
                with open(trash_file, 'rb') as f:
                    encoded = base64.b64encode(f.read()).decode('utf-8')
            except:
                pass
            if encoded:
                src = f"data:image/jpeg;base64,{encoded}"
                is_selected = (trash_file in selected_trash_items)
                restore_id = {'type': 'restore-btn', 'file_path': trash_file}
                checkbox_id = {'type': 'checkbox', 'file_path': trash_file}

                item_div = html.Div(
                    style={
                        'width': '100px',
                        'height': '130px',
                        'border': '1px solid #999',
                        'display': 'flex',
                        'flexDirection': 'column',
                        'alignItems': 'center',
                        'justifyContent': 'space-between',
                        'padding': '5px',
                        'backgroundColor': 'rgba(255,255,255,0.8)',
                        'position': 'relative'
                    },
                    children=[
                        # Чекбокс
                        html.Div(
                            style={'position': 'absolute', 'top': '3px', 'left': '3px'},
                            children=[
                                html.Img(
                                    src="/static/checkbox.png",
                                    id=checkbox_id,
                                    style={
                                        'width': '16px',
                                        'cursor': 'pointer',
                                        'opacity': '1.0' if is_selected else '0.5'
                                    }
                                )
                            ]
                        ),
                        # restore
                        html.Div(
                            style={'position': 'absolute', 'top': '3px', 'right': '3px'},
                            children=[
                                html.Img(
                                    src="/static/restore.png",
                                    id=restore_id,
                                    style={'width': '16px', 'cursor': 'pointer'}
                                )
                            ]
                        ),
                        html.Img(
                            src=src,
                            style={'width': '80px', 'height': '80px', 'objectFit': 'cover'}
                        ),
                        html.Div(img_name, style={'fontSize': '10px', 'textAlign': 'center', 'maxWidth': '80px'})
                    ]
                )
                children.append(item_div)

        # Кнопка красной корзины (mass delete)
        del_multiple_id = {'type': 'delete-multiple'}
        red_trash_btn = html.Div(
            style={
                'position': 'absolute',
                'bottom': '10px',
                'right': '10px',
                'cursor': 'pointer'
            },
            children=[
                html.Img(
                    src="/static/basket_red.png",
                    id=del_multiple_id,
                    style={'width': '72px', 'border': 'none'}
                )
            ]
        )
        children.append(red_trash_btn)

    return children

# ------------------------------------------------
# LAYOUT
# ------------------------------------------------
app.layout = html.Div(
    style={
        'height': '100vh',
        'display': 'flex',
        'flexDirection': 'column',
        'fontFamily': 'Segoe UI'
    },
    children=[

        # ШАПКА: логотип по центру
        html.Div(
            style={
                'backgroundColor': '#f0f0f0',
                'height': '50px',
                'display': 'flex',
                'justifyContent': 'center',
                'alignItems': 'center',
                'padding': '0 15px'
            },
            children=[
                html.Img(
                    src="/static/logo.png",
                    style={'height': '100%'}
                )
            ]
        ),

        # ВТОРАЯ ПОЛОСА: "Назад"/"Вперёд" + "Текущая папка:"
        html.Div(
            style={
                'backgroundColor': '#e0e0e0',
                'height': '40px',
                'display': 'flex',
                'alignItems': 'center',
                'padding': '0 15px',
                'gap': '20px'
            },
            children=[
                html.Img(src="/static/left_arrow.png", id="btn-back", style={'width': '30px', 'cursor': 'pointer'}),
                html.Img(src="/static/right_arrow.png", id="btn-forward", style={'width': '30px', 'cursor': 'pointer'}),
                html.Div("Текущая папка:", style={'fontWeight': 'bold'}),
                html.Div(id='current-folder-display', style={'color': '#333'})
            ]
        ),

        # ОСНОВНОЙ БЛОК: слева дерево, справа миниатюры
        html.Div(
            style={'display': 'flex', 'flex': 1, 'position': 'relative'},
            children=[
                html.Div(
                    id='folder-tree-container',
                    style={
                        'width': '350px',
                        'backgroundColor': '#333',
                        'color': 'white',
                        'padding': '10px',
                        'overflow': 'auto'
                    }
                ),
                html.Div(
                    id='thumbnails-container',
                    style={
                        'flex': 1,
                        'backgroundImage': 'url("/static/background.png")',
                        'backgroundRepeat': 'no-repeat',
                        'backgroundSize': 'cover',
                        'backgroundPosition': 'center',
                        'display': 'flex',
                        'flexWrap': 'wrap',
                        'gap': '10px',
                        'padding': '10px',
                        'overflow': 'auto',
                        'position': 'relative'
                    }
                )
            ]
        ),

        # МОДАЛЬНОЕ ОКНО: подтверждение удаления
        html.Div(
            id='confirm-modal',
            style={
                'display': 'none',
                'position': 'fixed',
                'top': '0', 'left': '0', 'right': '0', 'bottom': '0',
                'backgroundColor': 'rgba(0,0,0,0.8)',
                'justifyContent': 'center',
                'alignItems': 'center',
                'zIndex': '9999',
                'color': 'white',
                'fontSize': '20px'
            },
            children=[
                html.Div(
                    style={
                        'display': 'flex',
                        'flexDirection': 'column',
                        'alignItems': 'center',
                        'gap': '20px'
                    },
                    children=[
                        html.Div("Удалить выбранные изображения навсегда?"),
                        html.Div(
                            style={'display': 'flex', 'gap': '20px'},
                            children=[
                                html.Button("ДА", id="btn-confirm-yes", style={'backgroundColor': 'green', 'color': 'white', 'fontSize': '16px'}),
                                html.Button("НЕТ", id="btn-confirm-no", style={'backgroundColor': 'red', 'color': 'white', 'fontSize': '16px'})
                            ]
                        )
                    ]
                )
            ]
        ),

        # Хранилища
        dcc.Store(id='expanded-folders', data=[]),
        dcc.Store(id='folder-history', data=[ROOT_PATH]),
        dcc.Store(id='history-index', data=0),
        dcc.Store(id='selected-folder', data=ROOT_PATH),
        dcc.Store(id='selected-trash-items', data=[]),
        dcc.Store(id='confirm-modal-visible', data=False)
    ]
)

# ------------------------------------------------
# CALLBACKS
# ------------------------------------------------

# (A) Генерация дерева слева
@app.callback(
    Output('folder-tree-container', 'children'),
    Input('expanded-folders', 'data')
)
def update_left_tree(expanded_folders):
    return generate_tree(ROOT_PATH, expanded_folders)

# (B) Разворачиваем/сворачиваем папку
@app.callback(
    Output('expanded-folders', 'data', allow_duplicate=True),
    Input({'type': 'arrow', 'folder': dash.ALL}, 'n_clicks'),
    State('expanded-folders', 'data'),
    prevent_initial_call=True
)
def toggle_folder(n_clicks_list, expanded_folders):
    triggered_id = ctx.triggered_id
    if not isinstance(triggered_id, dict):
        return dash.no_update
    folder_path = triggered_id.get('folder')
    if folder_path in expanded_folders:
        return [f for f in expanded_folders if f != folder_path]
    else:
        return expanded_folders + [folder_path]

# (C) Клик по названию папки => добавляем её в историю
@app.callback(
    Output('folder-history', 'data', allow_duplicate=True),
    Output('history-index', 'data', allow_duplicate=True),
    Input({'type': 'folder-name', 'folder': dash.ALL}, 'n_clicks'),
    State('folder-history', 'data'),
    State('history-index', 'data'),
    prevent_initial_call=True
)
def select_folder(n_clicks_list, history, idx):
    triggered_id = ctx.triggered_id
    if not isinstance(triggered_id, dict):
        return dash.no_update, dash.no_update
    if triggered_id.get('type') != 'folder-name':
        return dash.no_update, dash.no_update

    new_folder = triggered_id.get('folder')
    if not new_folder:
        return dash.no_update, dash.no_update

    if idx < len(history) - 1:
        history = history[:idx + 1]
    if history and history[-1] == new_folder:
        return dash.no_update, dash.no_update

    history.append(new_folder)
    idx = len(history) - 1
    return history, idx

# (D) Отображаем current-folder
@app.callback(
    Output('selected-folder', 'data'),
    Output('current-folder-display', 'children'),
    Input('folder-history', 'data'),
    Input('history-index', 'data')
)
def sync_folder_and_label(history, idx):
    if idx < 0 or idx >= len(history):
        return ROOT_PATH, ROOT_PATH
    folder_path = history[idx]
    return folder_path, folder_path

# (E) Генерация миниатюр
@app.callback(
    Output('thumbnails-container', 'children'),
    Input('selected-folder', 'data'),
    State('selected-trash-items', 'data')
)
def update_thumbnails(folder_path, selected_trash_items):
    return build_thumbnails(folder_path, selected_trash_items)

# (F) Удаление (в корзину)
@app.callback(
    Output('thumbnails-container', 'children', allow_duplicate=True),
    Input({'type': 'basket-btn', 'file_path': dash.ALL}, 'n_clicks'),
    State('selected-folder', 'data'),
    State('selected-trash-items', 'data'),
    prevent_initial_call=True
)
def move_image_to_trash(n_clicks_list, folder_path, selected_trash_items):
    triggered_id = ctx.triggered_id
    if not isinstance(triggered_id, dict):
        return dash.no_update
    if not ctx.triggered or ctx.triggered[0]['prop_id'] == '.':
        return dash.no_update

    current_n_clicks = ctx.triggered[0]['value']
    if not current_n_clicks or current_n_clicks == 0:
        return dash.no_update

    file_to_delete = triggered_id.get('file_path')
    if not file_to_delete or not os.path.exists(file_to_delete):
        return dash.no_update

    # Переносим файл в TRASH
    file_name = os.path.basename(file_to_delete)
    new_path = os.path.join(TRASH_PATH, file_name)
    shutil.move(file_to_delete, new_path)
    TRASH_RECORDS[new_path] = file_to_delete

    return build_thumbnails(folder_path, selected_trash_items)

# (G) Чекбокс
@app.callback(
    Output('selected-trash-items', 'data', allow_duplicate=True),
    Input({'type': 'checkbox', 'file_path': dash.ALL}, 'n_clicks'),
    State('selected-trash-items', 'data'),
    prevent_initial_call=True
)
def toggle_checkbox(n_clicks_list, selected_items):
    triggered_id = ctx.triggered_id
    if not isinstance(triggered_id, dict):
        return dash.no_update
    if not ctx.triggered or ctx.triggered[0]['prop_id'] == '.':
        return dash.no_update

    current_n_clicks = ctx.triggered[0]['value']
    if not current_n_clicks or current_n_clicks == 0:
        return dash.no_update

    file_path = triggered_id.get('file_path')
    if file_path in selected_items:
        selected_items = [f for f in selected_items if f != file_path]
    else:
        selected_items.append(file_path)

    return selected_items

# (H) Восстановление из корзины
@app.callback(
    Output('thumbnails-container', 'children', allow_duplicate=True),
    Input({'type': 'restore-btn', 'file_path': dash.ALL}, 'n_clicks'),
    State('selected-folder', 'data'),
    State('selected-trash-items', 'data'),
    prevent_initial_call=True
)
def restore_file(n_clicks_list, folder_path, selected_trash_items):
    triggered_id = ctx.triggered_id
    if not isinstance(triggered_id, dict):
        return dash.no_update
    if not ctx.triggered or ctx.triggered[0]['prop_id'] == '.':
        return dash.no_update

    current_n_clicks = ctx.triggered[0]['value']
    if not current_n_clicks or current_n_clicks == 0:
        return dash.no_update

    trash_file = triggered_id.get('file_path')
    if not trash_file or not os.path.exists(trash_file):
        return dash.no_update

    if trash_file not in TRASH_RECORDS:
        return dash.no_update

    original_path = TRASH_RECORDS[trash_file]
    if not os.path.exists(os.path.dirname(original_path)):
        os.makedirs(os.path.dirname(original_path))
    shutil.move(trash_file, original_path)
    del TRASH_RECORDS[trash_file]

    return build_thumbnails(folder_path, selected_trash_items)

# (I) Модальное окно при массовом удалении
@app.callback(
    Output('confirm-modal-visible', 'data', allow_duplicate=True),
    Input({'type': 'delete-multiple'}, 'n_clicks'),
    [State('selected-trash-items', 'data'), State('selected-folder', 'data')],
    prevent_initial_call=True
)
def ask_confirmation_for_delete(n_clicks, selected_items, folder_path):
    if not n_clicks or n_clicks == 0:
        return dash.no_update
    if not selected_items:
        return dash.no_update
    return True

@app.callback(
    Output('confirm-modal', 'style'),
    Input('confirm-modal-visible', 'data')
)
def toggle_modal_display(is_visible):
    if is_visible:
        return {
            'display': 'flex',
            'position': 'fixed',
            'top': '0', 'left': '0', 'right': '0', 'bottom': '0',
            'backgroundColor': 'rgba(0,0,0,0.8)',
            'justifyContent': 'center',
            'alignItems': 'center',
            'zIndex': '9999',
            'color': 'white',
            'fontSize': '20px'
        }
    else:
        return {'display': 'none'}

@app.callback(
    Output('confirm-modal-visible', 'data', allow_duplicate=True),
    Output('thumbnails-container', 'children', allow_duplicate=True),
    Input('btn-confirm-yes', 'n_clicks'),
    Input('btn-confirm-no', 'n_clicks'),
    State('selected-trash-items', 'data'),
    State('selected-folder', 'data'),
    prevent_initial_call=True
)
def confirm_delete(yes_click, no_click, selected_items, folder_path):
    triggered_id = ctx.triggered_id
    if not triggered_id:
        return dash.no_update, dash.no_update

    if triggered_id == 'btn-confirm-no':
        # НЕТ
        return False, dash.no_update

    if triggered_id == 'btn-confirm-yes':
        # Удаляем все выделенные
        for file_path in selected_items:
            if os.path.exists(file_path):
                os.remove(file_path)
            if file_path in TRASH_RECORDS:
                del TRASH_RECORDS[file_path]
        selected_items = []
        return False, build_thumbnails(folder_path, selected_items)

    return dash.no_update, dash.no_update

# (J) Навигация Назад / Вперёд
@app.callback(
    Output('history-index', 'data', allow_duplicate=True),
    Input('btn-back', 'n_clicks'),
    Input('btn-forward', 'n_clicks'),
    State('history-index', 'data'),
    State('folder-history', 'data'),
    prevent_initial_call=True
)
def navigate_history(back_clicks, forward_clicks, idx, history):
    triggered_id = ctx.triggered_id
    if not history:
        return dash.no_update
    if triggered_id == 'btn-back':
        if idx > 0:
            return idx - 1
        else:
            return dash.no_update
    elif triggered_id == 'btn-forward':
        if idx < len(history) - 1:
            return idx + 1
        else:
            return dash.no_update

    return dash.no_update

# ------------------------------------------------
# КОЛЛБЭК: загрузка файлов
# ------------------------------------------------
@app.callback(
    Output('thumbnails-container', 'children', allow_duplicate=True),
    Input('upload-image', 'contents'),       # base64-списки
    State('upload-image', 'filename'),       # имена файлов
    State('selected-folder', 'data'),
    State('selected-trash-items', 'data'),
    prevent_initial_call=True
)
def upload_files(contents_list, filenames, folder_path, selected_trash_items):
    """
    При загрузке (через dcc.Upload) 
    - contents_list: список base64 строк "data:image/png;base64,AAAA..."
    - filenames: список имён
    - folder_path: куда сохранять (если не корзина - по желанию)
    """
    if not contents_list:
        return dash.no_update

   

    for content, fname in zip(contents_list, filenames):
        # content: "data:image/png;base64,iVBOR..."
        if 'base64,' not in content:
            continue
        base64_part = content.split('base64,')[1]
        file_path = os.path.join(folder_path, fname)
        with open(file_path, 'wb') as f:
            f.write(base64.b64decode(base64_part))

    return build_thumbnails(folder_path, selected_trash_items)

# ------------------------------------------------
# ЗАПУСК
# ------------------------------------------------
if __name__ == "__main__":
    app.run_server(debug=True, port=8050)
