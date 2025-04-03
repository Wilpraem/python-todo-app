import json
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.core.window import Window
from kivy.utils import get_color_from_hex, rgba
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Line

# --- Константы и функции для работы с данными ---
TASKS_FILE = "tasks.json"

def load_tasks():
    """Загружает задачи из файла JSON."""
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            tasks_data = json.load(f)
            # Проверка формата (оставляем только валидные словари)
            valid_tasks = [
                task for task in tasks_data
                if isinstance(task, dict) and 'description' in task and 'completed' in task
            ]
            return valid_tasks
    except (json.JSONDecodeError, IOError, TypeError) as e:
        print(f"Ошибка загрузки задач: {e}. Начинаем с пустого списка.")
        return []

def save_tasks(tasks):
    """Сохраняет задачи в файл JSON."""
    try:
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Ошибка сохранения задач: {e}")

# --- Стилизация (а-ля iOS Control Center) ---
BG_COLOR = get_color_from_hex('#F0F0F0') # Очень светло-серый фон
MODULE_BG = rgba('#FFFFFFE0') # Белый с ~88% непрозрачности
MODULE_BORDER = rgba('#00000020') # Очень легкая граница для модулей
TEXT_COLOR = get_color_from_hex('#000000')
ACCENT_COLOR = get_color_from_hex('#007AFF') # Синий iOS
DELETE_COLOR = get_color_from_hex('#FF3B30') # Красный iOS
DISABLED_TEXT_COLOR = get_color_from_hex('#8A8A8E') # Серый для зачеркнутого текста

Window.clearcolor = BG_COLOR
CORNER_RADIUS = dp(12) # Радиус скругления

# --- Kivy Виджеты с новым стилем ---

class RoundedBoxLayout(BoxLayout):
    """ BoxLayout с скругленным фоном """
    def __init__(self, bg_color=MODULE_BG, border_color=MODULE_BORDER, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.border_color = border_color
        with self.canvas.before:
            Color(rgba=self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[CORNER_RADIUS,])

        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class RoundedButton(Button):
    """ Кнопка со скругленным фоном """
    def __init__(self, bg_color=ACCENT_COLOR, text_color=get_color_from_hex('#FFFFFF'), corner_radius=CORNER_RADIUS, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0) # Стандартный фон прозрачный
        self.background_normal = ''
        self.background_down = ''
        self.color = text_color
        self.bold = True

        self._bg_color = bg_color
        self._corner_radius = corner_radius

        with self.canvas.before:
            Color(rgba=self._bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self._corner_radius,])

        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_state(self, instance, value):
        """ Изменение вида при нажатии """
        if value == 'down':
            r, g, b, a = self._bg_color
            self.rect.rgba = (r*0.8, g*0.8, b*0.8, a) # Затемняем
        else:
            self.rect.rgba = self._bg_color # Возвращаем исходный цвет


class TaskItem(RoundedBoxLayout):
    """ Виджет для отображения одной задачи """
    def __init__(self, task_data, app_instance, **kwargs):
        kwargs.pop('bg_color', None)
        kwargs.pop('border_color', None)
        super().__init__(bg_color=MODULE_BG, border_color=MODULE_BORDER, **kwargs)

        self.orientation = 'horizontal'
        self.padding = [dp(12), dp(8)]
        self.spacing = dp(10)
        self.size_hint_y = None
        self.height = dp(55)
        self.task_data = task_data
        self.app = app_instance

        self.checkbox = CheckBox(
            size_hint_x=None,
            width=dp(40),
            active=task_data['completed'],
            color=ACCENT_COLOR # Ожидает list/tuple, все верно
        )
        self.checkbox.bind(active=self.on_checkbox_active)
        self.add_widget(self.checkbox)

        self.label = Label(
            text=self.format_task_text(task_data['description'], task_data['completed']),
            color=TEXT_COLOR if not task_data['completed'] else DISABLED_TEXT_COLOR,
            markup=True,
            halign='left',
            valign='middle',
            size_hint_x=1,
            shorten=True,
            shorten_from='right',
            # Kivy < 2.1.0 может требовать ellipsis_options={'color':DISABLED_TEXT_COLOR}
            # Kivy >= 2.1.0 лучше использовать rgba
            ellipsis_options={'color':DISABLED_TEXT_COLOR, 'markup': True}
        )
        self.label.bind(size=self.label.setter('text_size'))
        self.add_widget(self.label)

        delete_button = RoundedButton(
            text='Del',
            size_hint_x=None,
            width=dp(50),
            bg_color=DELETE_COLOR,
            text_color=get_color_from_hex('#FFFFFF'),
            corner_radius=dp(8)
        )
        delete_button.bind(on_press=self.delete_task)
        self.add_widget(delete_button)

    def format_task_text(self, text, completed):
        """ Форматирует текст задачи (зачеркнутый и серый, если выполнена) """
        if completed:
            # Преобразуем цвет из list [r,g,b,a] в hex строку #rrggbb
            hex_color = '#%02x%02x%02x' % (int(DISABLED_TEXT_COLOR[0]*255), int(DISABLED_TEXT_COLOR[1]*255), int(DISABLED_TEXT_COLOR[2]*255))
            return f"[color={hex_color}][s]{text}[/s][/color]"
        else:
            return text

    def on_checkbox_active(self, checkbox, value):
        """ Обработчик изменения состояния чекбокса """
        self.task_data['completed'] = value
        self.label.text = self.format_task_text(self.task_data['description'], value)
        self.label.color = TEXT_COLOR if not value else DISABLED_TEXT_COLOR
        self.app.save_all_tasks()

    def delete_task(self, instance):
        """ Вызывает метод удаления в основном приложении """
        self.app.delete_task(self.task_data)


class TaskList(GridLayout):
    """ Контейнер для списка задач """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.spacing = dp(8)
        self.size_hint_y = None
        self.padding = [dp(10), dp(10)]
        self.bind(minimum_height=self.setter('height'))


class MainLayout(BoxLayout):
    """ Основной макет приложения """
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [dp(10), dp(10)]
        self.spacing = dp(15)
        self.app = app_instance

        # --- Верхняя часть: Поле ввода и кнопка добавления (модуль) ---
        add_area = RoundedBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(55),
            spacing=dp(10),
            padding=[dp(10)]
        )

        self.task_input = TextInput(
            hint_text='Новая задача...',
            multiline=False,
            size_hint_x=0.75,
            background_normal='',
            background_active='',
            background_color=(0,0,0,0), # Прозрачный фон
            foreground_color=TEXT_COLOR,
            cursor_color=ACCENT_COLOR,   # Ожидает list/tuple, все верно
            padding=[dp(10), dp(15)]
        )
        self.task_input.bind(on_text_validate=self.add_task_from_input) # Добавление по Enter

        add_button = RoundedButton(
            text='+',
            bold=True,
            size_hint_x=None,
            width=dp(50),
            bg_color=ACCENT_COLOR, # Передается в наш виджет, все верно
            text_color=get_color_from_hex('#FFFFFF'),
            corner_radius=dp(8)
        )
        add_button.bind(on_press=self.add_task_from_input)

        add_area.add_widget(self.task_input)
        add_area.add_widget(add_button)
        self.add_widget(add_area)

        # --- Средняя часть: Список задач с прокруткой ---
        scroll_view = ScrollView(
             size_hint=(1, 1),
             bar_width=dp(8),
             bar_color=ACCENT_COLOR, # <-- ИСПРАВЛЕНО: Просто передаем список [R,G,B,A]
             bar_inactive_color=rgba('#00000030')
             )
        self.task_list_layout = TaskList()
        scroll_view.add_widget(self.task_list_layout)
        self.add_widget(scroll_view)

        # --- Загрузка и отображение задач ---
        self.refresh_tasks_ui()

    def add_task_from_input(self, instance):
        """ Добавляет задачу из поля ввода """
        description = self.task_input.text.strip()
        if description:
            self.app.add_new_task(description)
            self.task_input.text = '' # Очищаем поле ввода
            self.refresh_tasks_ui() # Обновляем интерфейс

    def refresh_tasks_ui(self):
        """ Очищает и заново строит список задач в интерфейсе """
        self.task_list_layout.clear_widgets() # Удаляем старые виджеты
        # Добавляем актуальные задачи (новые сверху)
        for task_data in self.app.tasks: # Теперь не реверсируем, т.к. добавляем в начало
            task_widget = TaskItem(task_data=task_data, app_instance=self.app)
            self.task_list_layout.add_widget(task_widget)


class ToDoApp(App):
    """ Основной класс приложения Kivy """
    def build(self):
        self.title = 'To-Do List (iOS Inspired)'
        self.tasks = load_tasks() # Загружаем задачи при старте
        self.main_layout = MainLayout(app_instance=self)
        return self.main_layout

    def add_new_task(self, description):
        """ Добавляет новую задачу в список данных (в начало) """
        if description:
            self.tasks.insert(0, {'description': description, 'completed': False})
            self.save_all_tasks() # Сохраняем после добавления

    def delete_task(self, task_data_to_delete):
        """ Удаляет задачу из списка данных """
        try:
            self.tasks.remove(task_data_to_delete)
            self.save_all_tasks() # Сохраняем после удаления
            self.main_layout.refresh_tasks_ui() # Обновляем UI
        except ValueError:
            print("Не удалось найти задачу для удаления") # На всякий случай

    def save_all_tasks(self):
        """ Сохраняет текущий список задач в файл """
        save_tasks(self.tasks)

    def on_stop(self):
        """ Вызывается при закрытии приложения """
        self.save_all_tasks() # Гарантируем сохранение при выходе
        print("Задачи сохранены. Приложение закрывается.")


# --- Запуск приложения ---
if __name__ == '__main__':
    ToDoApp().run()
