import sys
import random
import json
import os
import re
import logging
from datetime import datetime

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Импорты для работы с PDF и OCR
# df[
try:
    import fitz  # PyMuPDF
    from PIL import Image
    import pytesseract
    import cv2
    import numpy as np
    from pdf2image import convert_from_path

    PDF_OCR_AVAILABLE = True
except ImportError as e:
    PDF_OCR_AVAILABLE = False
    print(f"Библиотеки для PDF не установлены: {e}")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'test_app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Пути к файлам тестов
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
USER_TESTS_DIR = os.path.join(BASE_DIR, 'user_tests')

# Создаем необходимые директории
for directory in [DATA_DIR, USER_TESTS_DIR]:
    os.makedirs(directory, exist_ok=True)

STATISTICS_PATH = os.path.join(DATA_DIR, 'statistics.json')
SETTINGS_PATH = os.path.join(DATA_DIR, 'settings.json')
CUSTOM_TESTS_FILE = os.path.join(DATA_DIR, 'custom_tests.json')


def load_available_tests():
    """Загрузить список доступных тестов (встроенные + пользовательские)"""
    tests = {
        '0-1': '0-1.json',
        '1-2': '1-2.json',
        '2-3': '2-3.json',
        '3-4': '3-4.json',
        '4-5': '4-5.json',
        '5-6': '5-6.json',
        '6-7': '6-7.json',
        'ПОТ ЭЭ (4 группа)': 'questions2.json',
        'ПТБТ' : 'ptbt.json',
        'птбт1' : 'ptbt1.json',
        'птбт2' : 'ptbt2.json',
        'птбт3' : 'ptbt3.json',
        'птбт4' : 'ptbt4.json'
    }

    # Загружаем пользовательские тесты
    if os.path.exists(CUSTOM_TESTS_FILE):
        try:
            with open(CUSTOM_TESTS_FILE, 'r', encoding='utf-8') as f:
                custom_tests = json.load(f)

            for test_name, test_info in custom_tests.items():
                if os.path.exists(test_info['path']):
                    tests[test_name] = f"user_tests/{test_info['filename']}"

        except Exception as e:
            logger.error(f"Ошибка загрузки пользовательских тестов: {e}")

    return tests


def load_questions(questions_path):
    try:
        if questions_path.startswith('user_tests/'):
            full_path = os.path.join(BASE_DIR, questions_path)
        else:
            full_path = os.path.join(DATA_DIR, questions_path)

        with open(full_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error(f"Файл не найден: {questions_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка JSON в файле {questions_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Ошибка загрузки вопросов: {e}")
        return []


def save_statistics(statistics):
    try:
        with open(STATISTICS_PATH, 'w', encoding='utf-8') as file:
            json.dump(statistics, file, ensure_ascii=False, indent=4)
        logger.info("Статистика сохранена")
    except Exception as e:
        logger.error(f"Ошибка сохранения статистики: {e}")


def load_statistics():
    try:
        with open(STATISTICS_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.info("Статистика не найдена, создана новая")
        return {"correct": 0, "incorrect": 0, "exams": 0, "marathons": 0}
    except json.JSONDecodeError:
        logger.error("Ошибка чтения статистики")
        return {"correct": 0, "incorrect": 0, "exams": 0, "marathons": 0}


def load_settings():
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as file:
            settings = json.load(file)
            if 'auto_next' not in settings:
                settings['auto_next'] = False
            if 'font_size' not in settings:
                settings['font_size'] = 11
            if 'delay_time' not in settings:
                settings['delay_time'] = 2
            return settings
    except FileNotFoundError:
        logger.info("Настройки не найдены, созданы по умолчанию")
        return {
            "auto_next": False,
            "font_size": 11,
            "delay_time": 2
        }
    except json.JSONDecodeError:
        logger.error("Ошибка чтения настроек")
        return {
            "auto_next": False,
            "font_size": 11,
            "delay_time": 2
        }


def save_settings(settings):
    try:
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as file:
            json.dump(settings, file, ensure_ascii=False, indent=4)
        logger.info("Настройки сохранены")
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек: {e}")


def save_custom_test(test_name, questions, test_type="custom"):
    """Сохранить пользовательский тест"""
    try:
        # Загружаем список пользовательских тестов
        custom_tests = {}
        if os.path.exists(CUSTOM_TESTS_FILE):
            try:
                with open(CUSTOM_TESTS_FILE, 'r', encoding='utf-8') as f:
                    custom_tests = json.load(f)
            except:
                pass

        # Генерируем имя файла
        safe_name = "".join(c for c in test_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        filename = f"{safe_name}.json"
        filepath = os.path.join(USER_TESTS_DIR, filename)

        # Сохраняем вопросы в формате приложения
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)

        # Обновляем список тестов
        custom_tests[test_name] = {
            'filename': filename,
            'path': filepath,
            'type': test_type,
            'created_at': datetime.now().isoformat(),
            'count': len(questions)
        }

        with open(CUSTOM_TESTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(custom_tests, f, ensure_ascii=False, indent=2)

        logger.info(f"Создан тест: {test_name} с {len(questions)} вопросами")
        return filepath
    except Exception as e:
        logger.error(f"Ошибка сохранения теста: {e}")
        raise


class ModernButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c6ea4;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)


class QuestionCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: 2px solid #ecf0f1;
                padding: 20px;
                margin: 10px;
            }
        """)


class PDFProcessingThread(QThread):
    progress = pyqtSignal(int)
    message = pyqtSignal(str, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, file_path, lang='rus+eng', dpi=300, method='direct_text'):
        super().__init__()
        self.file_path = file_path
        self.lang = lang
        self.dpi = dpi
        self.method = method
        self.questions = []

    def run(self):
        try:
            if not PDF_OCR_AVAILABLE:
                self.error.emit("Библиотеки для обработки PDF не установлены!")
                return

            logger.info(f"Начинаю обработку PDF: {self.file_path}, метод: {self.method}")
            logger.info(f"Размер файла: {os.path.getsize(self.file_path)} байт")
            self.message.emit("Начинаю обработку PDF...", "info")

            if self.method == 'direct_text':
                self.extract_text_directly()
            elif self.method == 'ocr':
                self.extract_with_ocr()
            elif self.method == 'hybrid':
                self.extract_hybrid()

            self.message.emit(f"✅ Найдено {len(self.questions)} вопросов", "success")
            self.finished.emit(self.questions)

        except Exception as e:
            logger.error(f"Ошибка обработки PDF: {e}")
            self.message.emit(f"❌ Ошибка: {str(e)}", "error")
            self.error.emit(str(e))

    def extract_text_directly(self):
        self.message.emit("Пытаюсь извлечь текст напрямую из PDF...", "info")

        try:
            doc = fitz.open(self.file_path)
            total_pages = len(doc)

            full_text = ""

            for page_num in range(total_pages):
                progress = int((page_num + 1) / total_pages * 100)
                self.progress.emit(progress)
                self.message.emit(f"Обрабатываю страницу {page_num + 1}/{total_pages}...", "info")

                page = doc.load_page(page_num)
                text = page.get_text("text")

                if page_num == 0:
                    logger.debug(f"=== ПЕРВАЯ СТРАНИЦА (первые 1000 символов) ===")
                    logger.debug(text[:1000])
                    logger.debug("=" * 80)

                full_text += text + "\n\n"

            doc.close()

            self.questions = self.parse_pdf_text(full_text)

        except Exception as e:
            logger.error(f"Ошибка извлечения текста напрямую: {e}")
            self.message.emit("Прямое извлечение не удалось, пробую OCR...", "info")
            self.extract_with_ocr()

    def extract_with_ocr(self):
        self.message.emit("Использую OCR для распознавания текста...", "info")

        poppler_path = None
        possible_paths = [
            '/opt/homebrew/bin',
            '/usr/local/bin',
            '/opt/homebrew/opt/poppler/bin',
        ]

        for path in possible_paths:
            if os.path.exists(os.path.join(path, 'pdftoppm')):
                poppler_path = path
                break

        if not poppler_path:
            raise Exception("Poppler не найден. Установите: brew install poppler")

        images = convert_from_path(
            self.file_path,
            poppler_path=poppler_path,
            dpi=150,
            thread_count=1,
            fmt='png'
        )

        total_pages = len(images)
        full_text = ""

        for i, image in enumerate(images):
            progress = int((i + 1) / total_pages * 100)
            self.progress.emit(progress)
            self.message.emit(f"Распознаю страницу {i + 1}/{total_pages}...", "info")

            try:
                text = pytesseract.image_to_string(
                    image,
                    lang=self.lang,
                    config='--psm 1 --oem 3'
                )
                full_text += text + "\n\n"

                if i == 0:
                    logger.debug(f"=== OCR СТРАНИЦА {i + 1} (первые 500 символов) ===")
                    logger.debug(text[:500])
                    logger.debug("=" * 80)

            except Exception as e:
                logger.error(f"Ошибка OCR на странице {i + 1}: {e}")
                continue

        self.questions = self.parse_pdf_text(full_text)

    def extract_hybrid(self):
        self.extract_text_directly()

        if len(self.questions) < 10:
            logger.warning(f"Прямым методом найдено мало вопросов ({len(self.questions)}), пробую OCR...")
            self.message.emit(f"Найдено мало вопросов, пробую OCR...", "info")
            self.extract_with_ocr()

    def parse_pdf_text(self, text):
        questions = []

        lines = [line.strip() for line in text.split('\n') if line.strip()]

        if not lines:
            logger.warning("Нет текста для парсинга")
            return questions

        logger.info(f"Всего строк после очистки: {len(lines)}")

        full_text = ' '.join(lines)

        question_patterns = [
            r'ВОПРОС\s+№?\s*(\d+)(?:\s*[-–]\s*\d+)?',
            r'Вопрос\s+№?\s*(\d+)',
            r'^\s*(\d+)[\.\)]\s+',
        ]

        question_sections = []
        current_section = []

        for i, line in enumerate(lines):
            is_question_start = False

            for pattern in question_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    is_question_start = True
                    break

            if '?' in line and len(line) > 10 and not is_question_start:
                if not re.match(r'^\d+[\.\)]', line) and not re.match(r'^[а-гa-d][\.\)]', line, re.IGNORECASE):
                    is_question_start = True

            if is_question_start and current_section:
                question_sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)

        if current_section:
            question_sections.append('\n'.join(current_section))

        logger.info(f"Найдено {len(question_sections)} потенциальных блоков вопросов")

        for block_idx, block in enumerate(question_sections):
            try:
                question = self.parse_single_question_block(block, block_idx + 1)
                if question and question.get('answers'):
                    questions.append(question)
                    logger.info(f"Добавлен вопрос #{block_idx + 1} с {len(question['answers'])} ответами")
            except Exception as e:
                logger.error(f"Ошибка парсинга блока {block_idx + 1}: {e}")
                logger.debug(f"Проблемный блок {block_idx + 1}:\n{block[:200]}...")

        return questions

    def parse_single_question_block(self, block_text, question_num):
        lines = [line.strip() for line in block_text.split('\n') if line.strip()]

        if len(lines) < 3:
            return None

        question_start_idx = 0
        for i, line in enumerate(lines):
            if '?' in line and len(line) > 10:
                question_start_idx = i
                break

        question_lines = []
        answer_start_idx = len(lines)

        for i in range(question_start_idx, len(lines)):
            line = lines[i]

            if (re.match(r'^\d+[\.\)]', line) or
                    re.match(r'^[а-гa-d][\.\)]', line, re.IGNORECASE)):
                answer_start_idx = i
                break

            question_lines.append(line)

        question_text = ' '.join(question_lines).strip()

        question_text = re.sub(r'^(ВОПРОС\s+№?\s*\d+\s*[-–]?\s*\d*\s*[:\.]?\s*)', '', question_text,
                               flags=re.IGNORECASE)
        question_text = re.sub(r'^(Вопрос\s+№?\s*\d+\s*[:\.]?\s*)', '', question_text, flags=re.IGNORECASE)
        question_text = re.sub(r'^\d+[\.\)]\s*', '', question_text)

        answers = []
        correct_answers = []
        current_answer = ""
        current_answer_num = 0

        for i in range(answer_start_idx, len(lines)):
            line = lines[i]

            answer_match = re.match(r'^(\d+)[\.\)]\s*(.*)', line)
            letter_match = re.match(r'^([а-гa-d])[\.\)]\s*(.*)', line, re.IGNORECASE)

            if answer_match or letter_match:
                if current_answer:
                    answers.append(current_answer.strip())

                    is_correct = self.check_if_answer_is_correct(current_answer)
                    if is_correct:
                        correct_answers.append(len(answers) - 1)

                if answer_match:
                    current_answer_num = int(answer_match.group(1))
                    current_answer = answer_match.group(2)
                else:
                    letter = letter_match.group(1).lower()
                    letter_to_num = {'а': 1, 'a': 1, 'б': 2, 'b': 2, 'в': 3, 'c': 3, 'г': 4, 'd': 4}
                    current_answer_num = letter_to_num.get(letter, len(answers) + 1)
                    current_answer = letter_match.group(2)
            elif current_answer:
                current_answer += " " + line

        if current_answer:
            answers.append(current_answer.strip())
            is_correct = self.check_if_answer_is_correct(current_answer)
            if is_correct:
                correct_answers.append(len(answers) - 1)

        if not answers:
            return None

        question = {
            'id': question_num,
            'question': question_text,
            'answers': answers,
            'correct': correct_answers,
            'explanation': '',
            'source': 'pdf_direct_extract'
        }

        return question

    def check_if_answer_is_correct(self, answer_text):
        correct_patterns = [
            r'\(верно\)',
            r'\(правильно\)',
            r'\(correct\)',
            r'\(true\)',
            r'\*\(верно\)\*',
            r'\*\(правильно\)\*',
            r'✓',
            r'✔',
            r'\+',
            r'\[верно\]',
            r'\[правильно\]',
            r'верный\s+ответ',
            r'правильный\s+ответ',
        ]

        answer_lower = answer_text.lower()

        for pattern in correct_patterns:
            if re.search(pattern, answer_lower):
                return True

        return False


class PDFImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Импорт вопросов из PDF")
        self.setGeometry(200, 200, 800, 600)
        self.parent = parent
        self.questions = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        file_layout = QHBoxLayout()
        self.file_label = QLabel("Файл не выбран")
        self.file_label.setStyleSheet("color: #666; font-style: italic;")
        btn_select = ModernButton("📁 Выбрать PDF...")
        btn_select.clicked.connect(self.select_file)
        file_layout.addWidget(btn_select)
        file_layout.addWidget(self.file_label, 1)
        layout.addLayout(file_layout)

        params_group = QGroupBox("Параметры обработки")
        params_layout = QVBoxLayout()

        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "Авто (рекомендуется)",
            "Прямое извлечение текста",
            "OCR распознавание",
            "Гибридный"
        ])
        params_layout.addWidget(QLabel("Метод обработки:"))
        params_layout.addWidget(self.method_combo)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Русский+Английский", "Только русский", "Только английский"])
        params_layout.addWidget(QLabel("Язык (для OCR):"))
        params_layout.addWidget(self.lang_combo)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(100, 300)
        self.dpi_spin.setValue(150)
        params_layout.addWidget(QLabel("DPI (для OCR):"))
        params_layout.addWidget(self.dpi_spin)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                color: #2c3e50;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.log_text)

        btn_layout = QHBoxLayout()
        self.btn_process = ModernButton("🔍 Начать обработку")
        self.btn_process.clicked.connect(self.process_pdf)
        self.btn_process.setEnabled(False)
        self.btn_process.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)

        btn_close = ModernButton("Закрыть")
        btn_close.clicked.connect(self.close)

        btn_layout.addWidget(self.btn_process)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        preview_label = QLabel("Найденные вопросы:")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 20px; color: #2c3e50;")
        layout.addWidget(preview_label)

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(["Вопрос", "Варианты ответов", "Правильный"])
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.setStyleSheet("""
            QTableWidget {
                font-size: 12px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
            QTableWidget::item {
                color: #2c3e50;
            }
        """)
        layout.addWidget(self.preview_table, 1)

        preview_buttons = QHBoxLayout()
        self.btn_save = ModernButton("💾 Сохранить как тест")
        self.btn_save.clicked.connect(self.save_as_test)
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)

        self.btn_export = ModernButton("📤 Экспорт в JSON")
        self.btn_export.clicked.connect(self.export_to_json)
        self.btn_export.setEnabled(False)

        preview_buttons.addWidget(self.btn_save)
        preview_buttons.addWidget(self.btn_export)
        preview_buttons.addStretch()
        layout.addLayout(preview_buttons)

        self.setLayout(layout)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите PDF файл",
            "",
            "PDF Files (*.pdf)"
        )

        if file_path:
            self.file_path = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.file_label.setStyleSheet("color: #2c3e50; font-weight: bold;")
            self.btn_process.setEnabled(True)
            self.log_message(f"Выбран файл: {os.path.basename(file_path)}")

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def process_pdf(self):
        if not hasattr(self, 'file_path'):
            return

        self.btn_process.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()

        self.log_message("Начинаю обработку PDF...")

        lang_map = {
            "Русский+Английский": "rus+eng",
            "Только русский": "rus",
            "Только английский": "eng"
        }
        selected_lang = self.lang_combo.currentText()
        lang = lang_map.get(selected_lang, "rus+eng")

        method_map = {
            "Авто (рекомендуется)": "direct_text",
            "Прямое извлечение текста": "direct_text",
            "OCR распознавание": "ocr",
            "Гибридный": "hybrid"
        }
        selected_method = self.method_combo.currentText()
        method = method_map.get(selected_method, "direct_text")

        dpi = self.dpi_spin.value() if selected_method in ["OCR распознавание", "Гибридный"] else 150

        self.log_message(f"Метод: {selected_method}, Язык: {selected_lang}, DPI: {dpi}")

        self.thread = PDFProcessingThread(
            self.file_path,
            lang=lang,
            dpi=dpi,
            method=method
        )
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.message.connect(self.handle_message)
        self.thread.finished.connect(self.on_processing_finished)
        self.thread.error.connect(self.show_error)
        self.thread.start()

    def handle_message(self, message, level):
        self.log_message(message)
        if level == "error":
            logger.error(message)
        elif level == "info":
            logger.info(message)
        elif level == "success":
            logger.info(message)

    def show_error(self, error):
        self.log_message(f"❌ Ошибка: {error}")
        QMessageBox.critical(self, "Ошибка", error)
        self.progress_bar.setVisible(False)
        self.btn_process.setEnabled(True)

    def on_processing_finished(self, questions):
        self.questions = questions
        self.progress_bar.setVisible(False)
        self.btn_process.setEnabled(True)
        self.btn_save.setEnabled(len(questions) > 0)
        self.btn_export.setEnabled(len(questions) > 0)

        self.preview_table.setRowCount(len(questions))

        for i, q in enumerate(questions):
            question_text = q.get('question', '')
            if len(question_text) > 100:
                question_text = question_text[:100] + "..."
            question_item = QTableWidgetItem(question_text)
            question_item.setToolTip(q.get('question', ''))
            self.preview_table.setItem(i, 0, question_item)

            answers_text = ""
            for j, ans in enumerate(q.get('answers', [])):
                if j < len(q.get('answers', [])):
                    prefix = "✓ " if j in q.get('correct', []) else "  "
                    answers_text += f"{prefix}{j + 1}) {ans}\n"
            answers_item = QTableWidgetItem(answers_text.strip())
            answers_item.setToolTip(answers_text)
            self.preview_table.setItem(i, 1, answers_item)

            correct_text = ", ".join([str(idx + 1) for idx in q.get('correct', [])])
            if not correct_text:
                correct_text = "Не определены"
            correct_item = QTableWidgetItem(correct_text)
            self.preview_table.setItem(i, 2, correct_item)

        self.log_message(f"✅ Обработка завершена! Найдено {len(questions)} вопросов")

        if questions:
            correct_count = sum(1 for q in questions if q.get('correct'))
            self.log_message(f"Из них с правильными ответами: {correct_count}")

        QMessageBox.information(self, "Успех",
                                f"✅ Найдено {len(questions)} вопросов!\n\n"
                                f"Из них с вариантами ответов: {sum(1 for q in questions if q['answers'])}\n"
                                f"С правильными ответами: {sum(1 for q in questions if q['correct'])}")

    def save_as_test(self):
        if not self.questions:
            return

        test_name, ok = QInputDialog.getText(
            self, "Сохранение теста",
            "Введите название теста:",
            text=os.path.basename(self.file_path).replace('.pdf', '')
        )

        if not ok or not test_name.strip():
            return

        try:
            filepath = save_custom_test(test_name.strip(), self.questions)

            if self.parent:
                self.parent.add_test_to_menu(test_name, filepath)

            QMessageBox.information(self, "✅ Успех",
                                    f"Тест '{test_name}' успешно создан и добавлен в меню!\n\n"
                                    f"📁 Файл: {os.path.basename(filepath)}\n"
                                    f"📊 Вопросов: {len(self.questions)}\n"
                                    f"📍 Сохранено в: {USER_TESTS_DIR}")

            self.log_message(f"Тест сохранен: {test_name}")
            self.accept()

        except Exception as e:
            self.log_message(f"❌ Ошибка сохранения: {str(e)}")
            QMessageBox.critical(self, "❌ Ошибка", f"Не удалось сохранить тест:\n{str(e)}")

    def export_to_json(self):
        if not self.questions:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить вопросы как JSON",
            f"{os.path.basename(self.file_path).replace('.pdf', '')}_questions.json",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.questions, f, ensure_ascii=False, indent=2)

                self.log_message(f"Вопросы экспортированы в: {file_path}")
                QMessageBox.information(self, "Успех",
                                        f"✅ Вопросы экспортированы в:\n{file_path}\n\n"
                                        f"📊 Всего вопросов: {len(self.questions)}")
            except Exception as e:
                self.log_message(f"❌ Ошибка экспорта: {str(e)}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{str(e)}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Тестирование Норникель")
        self.setGeometry(100, 100, 1000, 700)

        self.settings = load_settings()
        self.statistics = load_statistics()

        self.available_tests = load_available_tests()

        self.current_mode = None
        self.current_questions = []
        self.current_index = 0
        self.current_errors = 0
        self.wrong_answers = []
        self.show_results = False

        self.current_test_name = None
        self.current_test_file = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        self.create_menu_page()
        self.create_test_page()
        self.create_settings_page()

        self.create_menu_bar()

        self.questions = self.load_initial_questions()

        self.show_menu()

        logger.info("Приложение запущено")

    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

    def create_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("📁 Файл")

        import_action = QAction("📄 Импорт из PDF...", self)
        import_action.triggered.connect(self.open_pdf_import_dialog)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        exit_action = QAction("🚪 Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tests_menu = menubar.addMenu("📚 Тесты")

        refresh_action = QAction("🔄 Обновить список тестов", self)
        refresh_action.triggered.connect(self.refresh_tests_list)
        tests_menu.addAction(refresh_action)

        create_empty_action = QAction("✏️ Создать пустой тест", self)
        create_empty_action.triggered.connect(self.create_empty_test)
        tests_menu.addAction(create_empty_action)

        tests_menu.addSeparator()

        self.test_actions = {}
        self.update_tests_menu()

    def update_tests_menu(self):
        menubar = self.menuBar()
        for action_obj in menubar.actions():
            if action_obj.text() == "📚 Тесты":
                tests_menu = action_obj.menu()

                actions_to_remove = []
                for action in tests_menu.actions():
                    if action.text() not in ["🔄 Обновить список тестов", "✏️ Создать пустой тест"]:
                        actions_to_remove.append(action)

                for action in actions_to_remove:
                    tests_menu.removeAction(action)

                if self.available_tests:
                    tests_menu.addSeparator()

                for test_name in self.available_tests.keys():
                    action = QAction(f"📝 {test_name}", self)
                    action.triggered.connect(lambda checked, tn=test_name: self.load_test(tn))
                    tests_menu.addAction(action)
                    self.test_actions[test_name] = action
                break

    def add_test_to_menu(self, test_name, filepath):
        rel_path = os.path.relpath(filepath, BASE_DIR)
        self.available_tests[test_name] = rel_path

        self.update_tests_menu()

        self.update_test_buttons()

        self.load_test(test_name)

    def refresh_tests_list(self):
        self.available_tests = load_available_tests()

        self.update_tests_menu()

        self.update_test_buttons()

        logger.info("Список тестов обновлен")
        QMessageBox.information(self, "Обновлено", "Список тестов обновлен!")

    def create_empty_test(self):
        test_name, ok = QInputDialog.getText(
            self, "Создание теста",
            "Введите название теста:"
        )

        if not ok or not test_name.strip():
            return

        empty_questions = []
        try:
            filepath = save_custom_test(test_name.strip(), empty_questions)

            self.add_test_to_menu(test_name, filepath)

            logger.info(f"Создан пустой тест: {test_name}")
            QMessageBox.information(self, "✅ Успех",
                                    f"Пустой тест '{test_name}' создан!\n\n"
                                    f"Теперь вы можете добавить вопросы через:\n"
                                    f"1. 📁 Файл → 📄 Импорт из PDF\n"
                                    f"2. Или добавить вопросы вручную в файле:\n"
                                    f"{filepath}")

        except Exception as e:
            logger.error(f"Ошибка создания теста: {e}")
            QMessageBox.critical(self, "❌ Ошибка", f"Не удалось создать тест:\n{str(e)}")

    def open_pdf_import_dialog(self):
        if not PDF_OCR_AVAILABLE:
            QMessageBox.warning(self, "Библиотеки не установлены",
                                "Для импорта из PDF нужны дополнительные библиотеки.\n\n"
                                "Установите:\n"
                                "pip install PyMuPDF pytesseract pillow pdf2image opencv-python\n\n"
                                "А также системные зависимости:\n"
                                "brew install poppler tesseract tesseract-lang")
            return

        dialog = PDFImportDialog(self)
        dialog.exec()

    def load_initial_questions(self):
        if self.available_tests:
            first_test = list(self.available_tests.keys())[0]
            return self.load_test(first_test, silent=True)
        return []

    def load_test(self, test_name, silent=False):
        if test_name not in self.available_tests:
            if not silent:
                QMessageBox.critical(self, "Ошибка", f"Тест '{test_name}' не найден!")
            return []

        test_file = self.available_tests[test_name]

        if test_file.startswith('user_tests/'):
            test_path = os.path.join(BASE_DIR, test_file)
        else:
            test_path = os.path.join(DATA_DIR, test_file)

        if not os.path.exists(test_path):
            if not silent:
                QMessageBox.critical(self, "Ошибка", f"Файл теста не найден!\nПуть: {test_path}")
            return []

        questions = load_questions(test_file)
        if not questions and not silent:
            QMessageBox.warning(self, "Предупреждение", f"Тест '{test_name}' пуст или поврежден!")
            return []

        self.questions = questions
        self.current_test_name = test_name
        self.current_test_file = test_file
        self.wrong_answers = []

        if hasattr(self, 'test_info_label'):
            self.update_test_info()

        logger.info(f"Загружен тест: {test_name} ({len(questions)} вопросов)")

        if not silent:
            QMessageBox.information(self, "Успех",
                                    f"✅ Тест '{test_name}' успешно загружен!\n\n"
                                    f"Всего вопросов: {len(self.questions)}")

        return questions

    def create_menu_page(self):
        self.menu_page = QWidget()
        layout = QVBoxLayout(self.menu_page)

        title_layout = QVBoxLayout()
        title_label = QLabel("Тестирование по охране труда")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                padding: 20px;
            }
        """)
        title_layout.addWidget(title_label)

        subtitle_label = QLabel("в электроустановках")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                color: #34495e;
                padding-bottom: 30px;
            }
        """)
        title_layout.addWidget(subtitle_label)
        layout.addLayout(title_layout)

        modes_frame = QFrame()
        modes_frame.setStyleSheet("background-color: transparent;")
        modes_layout = QVBoxLayout(modes_frame)

        modes = [
            ("📝 ЭКЗАМЕН", self.start_exam),
            ("🏃 МАРАФОН", self.start_marathon),
            ("⚠️ ПОВТОРЕНИЕ ОШИБОК", self.start_errors),
            ("📊 СТАТИСТИКА", self.show_statistics),
            ("⚙️ НАСТРОЙКИ", self.show_settings)
        ]

        for text, handler in modes:
            btn = ModernButton(text)
            btn.clicked.connect(handler)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 15px;
                    margin: 8px 50px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            modes_layout.addWidget(btn)

        layout.addWidget(modes_frame)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #bdc3c7; margin: 30px 50px;")
        layout.addWidget(separator)

        test_selection_layout = QVBoxLayout()
        test_label = QLabel("Выберите тест:")
        test_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                margin-left: 50px;
                margin-bottom: 10px;
            }
        """)
        test_selection_layout.addWidget(test_label)

        self.test_buttons_container = QWidget()
        self.test_buttons_layout = QHBoxLayout(self.test_buttons_container)
        self.test_buttons_layout.setContentsMargins(50, 0, 50, 10)

        self.test_buttons = {}
        self.test_buttons_layout.addWidget(QLabel("Загрузка тестов..."))

        test_selection_layout.addWidget(self.test_buttons_container)
        layout.addLayout(test_selection_layout)

        self.test_info_card = QuestionCard()
        test_info_layout = QVBoxLayout(self.test_info_card)
        self.test_info_label = QLabel("Загрузка информации о тесте...")
        self.test_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.test_info_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #2c3e50;
                padding: 15px;
            }
        """)
        test_info_layout.addWidget(self.test_info_label)
        layout.addWidget(self.test_info_card, 0, Qt.AlignmentFlag.AlignHCenter)

        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(50, 20, 50, 20)

        self.questions_count_label = QLabel("Вопросы: 0")
        self.questions_count_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        info_layout.addWidget(self.questions_count_label)

        info_layout.addStretch()

        self.menu_error_label = QLabel("Ошибок: 0")
        self.menu_error_label.setStyleSheet("color: #e74c3c; font-size: 12px; font-weight: bold;")
        info_layout.addWidget(self.menu_error_label)

        layout.addLayout(info_layout)

        layout.addStretch()

        self.stacked_widget.addWidget(self.menu_page)

    def update_test_buttons(self):
        while self.test_buttons_layout.count():
            item = self.test_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.test_buttons = {}

        for test_name in self.available_tests.keys():
            btn = ModernButton(test_name)
            btn.clicked.connect(lambda checked, tn=test_name: self.load_test(tn))

            if test_name == self.current_test_name:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3498db;
                        color: white;
                        padding: 10px 20px;
                        margin: 5px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #2980b9;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ecf0f1;
                        color: #2c3e50;
                        padding: 10px 20px;
                        margin: 5px;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #d5dbdb;
                    }
                """)

            self.test_buttons_layout.addWidget(btn)
            self.test_buttons[test_name] = btn

    def update_test_info(self):
        if not hasattr(self, 'test_info_label'):
            return

        if self.current_test_name:
            test_info = f"📋 Текущий тест: {self.current_test_name}"

            if self.current_test_file:
                if self.current_test_file.startswith('user_tests/'):
                    test_info += " (пользовательский)"
                else:
                    test_info += f" ({self.current_test_file})"

            test_info += f"\n📊 Вопросов в базе: {len(self.questions)}"

            self.test_info_label.setText(test_info)
        else:
            self.test_info_label.setText("❌ Тест не загружен! Выберите тест из списка выше.")

        if hasattr(self, 'questions_count_label'):
            self.questions_count_label.setText(f"Всего вопросов: {len(self.questions)}")

        if hasattr(self, 'menu_error_label'):
            if self.wrong_answers:
                self.menu_error_label.setText(f"⚠️ Вопросов с ошибками: {len(self.wrong_answers)}")
            else:
                self.menu_error_label.setText("✅ Нет ошибок")

        if not self.test_buttons and hasattr(self, 'test_buttons_layout'):
            self.update_test_buttons()

    def create_test_page(self):
        self.test_page = QWidget()
        layout = QVBoxLayout(self.test_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_panel = QFrame()
        top_panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom: 2px solid #ecf0f1;
                padding: 5px;
            }
        """)
        top_layout = QHBoxLayout(top_panel)

        self.mode_label = QLabel("Режим")
        self.mode_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #3498db;
                padding: 10px;
            }
        """)
        top_layout.addWidget(self.mode_label)

        progress_layout = QVBoxLayout()
        self.question_num_label = QLabel("Вопрос 0/0")
        self.question_num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.question_num_label.setStyleSheet("color: #2c3e50; font-size: 14px;")
        progress_layout.addWidget(self.question_num_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                margin: 5px 50px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 5px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        top_layout.addLayout(progress_layout)

        right_layout = QVBoxLayout()
        self.error_label = QLabel("Ошибок: 0")
        self.error_label.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 14px;")
        right_layout.addWidget(self.error_label)

        self.test_info_test_label = QLabel("Тест не выбран")
        self.test_info_test_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        right_layout.addWidget(self.test_info_test_label)
        top_layout.addLayout(right_layout)

        layout.addWidget(top_panel)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #f5f6fa;
            }
            QScrollBar:vertical {
                border: none;
                background: #f5f6fa;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #bdc3c7;
                min-height: 30px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        self.test_content = QWidget()
        self.test_content_layout = QVBoxLayout(self.test_content)
        self.test_content_layout.setContentsMargins(20, 20, 20, 20)
        self.test_content_layout.setSpacing(15)

        self.question_card = QuestionCard()
        question_card_layout = QVBoxLayout(self.question_card)
        question_card_layout.setContentsMargins(25, 25, 25, 25)

        self.question_label = QLabel("Выберите тест и начните тестирование")
        self.question_label.setWordWrap(True)
        self.question_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.question_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin: 10px;
            }
        """)
        question_card_layout.addWidget(self.question_label)
        self.test_content_layout.addWidget(self.question_card)

        self.question_type_label = QLabel("")
        self.question_type_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #3498db;
                font-weight: bold;
                padding: 10px 20px;
                margin-top: 10px;
            }
        """)
        self.test_content_layout.addWidget(self.question_type_label)

        self.answers_frame = QFrame()
        self.answers_frame.setStyleSheet("background-color: transparent;")
        self.answers_layout = QVBoxLayout(self.answers_frame)
        self.answers_layout.setContentsMargins(10, 10, 10, 10)
        self.answers_layout.setSpacing(8)
        self.test_content_layout.addWidget(self.answers_frame)

        self.test_content_layout.addStretch()

        scroll_area.setWidget(self.test_content)
        layout.addWidget(scroll_area, 1)

        bottom_panel = QFrame()
        bottom_panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border-top: 2px solid #ecf0f1;
                padding: 10px;
            }
        """)
        bottom_layout = QHBoxLayout(bottom_panel)

        self.back_button = ModernButton("← Назад в меню")
        self.back_button.clicked.connect(self.show_menu)
        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                padding: 12px 24px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        bottom_layout.addWidget(self.back_button)

        bottom_layout.addStretch()

        self.answer_button = ModernButton("ПРОВЕРИТЬ ОТВЕТ")
        self.answer_button.clicked.connect(self.check_answer)
        self.answer_button.setEnabled(False)
        self.answer_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                font-weight: bold;
                padding: 15px 30px;
                min-width: 200px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #219653;
            }
        """)
        bottom_layout.addWidget(self.answer_button)

        bottom_layout.addStretch()

        self.next_button = ModernButton("СЛЕДУЮЩИЙ ВОПРОС →")
        self.next_button.clicked.connect(self.next_question)
        self.next_button.setEnabled(False)
        self.next_button.setStyleSheet("""
            QPushButton {
                min-width: 200px;
                padding: 12px 24px;
                font-size: 16px;
            }
        """)
        bottom_layout.addWidget(self.next_button)

        layout.addWidget(bottom_panel)

        self.stacked_widget.addWidget(self.test_page)

    def create_settings_page(self):
        self.settings_page = QWidget()
        layout = QVBoxLayout(self.settings_page)

        title_label = QLabel("НАСТРОЙКИ")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                padding: 30px;
            }
        """)
        layout.addWidget(title_label)

        self.settings_test_info_card = QuestionCard()
        settings_test_info_layout = QVBoxLayout(self.settings_test_info_card)
        self.settings_test_info_label = QLabel("Тест не загружен")
        self.settings_test_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.settings_test_info_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #2c3e50;
                padding: 15px;
            }
        """)
        settings_test_info_layout.addWidget(self.settings_test_info_label)
        layout.addWidget(self.settings_test_info_card, 0, Qt.AlignmentFlag.AlignHCenter)

        settings_card = QuestionCard()
        settings_card_layout = QVBoxLayout(settings_card)

        auto_next_layout = QHBoxLayout()
        self.auto_next_checkbox = QCheckBox("Автоматический переход к следующему вопросу")
        self.auto_next_checkbox.setChecked(self.settings['auto_next'])
        self.auto_next_checkbox.stateChanged.connect(self.update_auto_next_setting)
        self.auto_next_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                color: #2c3e50;
                padding: 15px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        auto_next_layout.addWidget(self.auto_next_checkbox)
        settings_card_layout.addLayout(auto_next_layout)

        font_size_layout = QHBoxLayout()
        font_size_label = QLabel("Размер шрифта:")
        font_size_label.setStyleSheet("font-size: 14px; color: #2c3e50; padding: 15px;")
        font_size_layout.addWidget(font_size_label)

        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 20)
        self.font_size_spinbox.setValue(self.settings['font_size'])
        self.font_size_spinbox.valueChanged.connect(self.update_font_size_setting)
        font_size_layout.addWidget(self.font_size_spinbox)
        font_size_layout.addStretch()
        settings_card_layout.addLayout(font_size_layout)

        delay_layout = QHBoxLayout()
        delay_label = QLabel("Задержка перед авто-переходом (сек):")
        delay_label.setStyleSheet("font-size: 14px; color: #2c3e50; padding: 15px;")
        delay_layout.addWidget(delay_label)

        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(1, 10)
        self.delay_spinbox.setValue(self.settings['delay_time'])
        self.delay_spinbox.valueChanged.connect(self.update_delay_setting)
        delay_layout.addWidget(self.delay_spinbox)
        delay_layout.addStretch()
        settings_card_layout.addLayout(delay_layout)

        reset_layout = QVBoxLayout()
        reset_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.reset_button = ModernButton("СБРОСИТЬ СТАТИСТИКУ")
        self.reset_button.clicked.connect(self.reset_statistics)
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                padding: 15px 30px;
                margin: 20px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        reset_layout.addWidget(self.reset_button)

        reset_warning = QLabel("Внимание: сброс статистики не удалит вопросы с ошибками")
        reset_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reset_warning.setStyleSheet("color: #e74c3c; font-size: 12px;")
        reset_layout.addWidget(reset_warning)

        settings_card_layout.addLayout(reset_layout)
        layout.addWidget(settings_card)

        back_layout = QHBoxLayout()
        back_layout.addStretch()

        back_button = ModernButton("← Назад в меню")
        back_button.clicked.connect(self.show_menu)
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                margin: 30px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        back_layout.addWidget(back_button)

        back_layout.addStretch()
        layout.addLayout(back_layout)

        layout.addStretch()
        self.stacked_widget.addWidget(self.settings_page)

    def update_auto_next_setting(self):
        self.settings['auto_next'] = self.auto_next_checkbox.isChecked()
        save_settings(self.settings)
        logger.info(f"Настройка auto_next изменена на: {self.settings['auto_next']}")

    def update_font_size_setting(self, value):
        self.settings['font_size'] = value
        save_settings(self.settings)
        logger.info(f"Настройка font_size изменена на: {value}")

    def update_delay_setting(self, value):
        self.settings['delay_time'] = value
        save_settings(self.settings)
        logger.info(f"Настройка delay_time изменена на: {value}")

    def reset_statistics(self):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите сбросить статистику?\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.statistics = {"correct": 0, "incorrect": 0, "exams": 0, "marathons": 0}
            save_statistics(self.statistics)
            logger.info("Статистика сброшена")
            QMessageBox.information(self, "Статистика", "Статистика сброшена.")

    def show_settings(self):
        if self.current_test_name:
            test_info = f"📋 Текущий тест: {self.current_test_name}"
            if self.current_test_file:
                if self.current_test_file.startswith('user_tests/'):
                    test_info += " (пользовательский)"
                else:
                    test_info += f" ({self.current_test_file})"
            self.settings_test_info_label.setText(test_info)
        else:
            self.settings_test_info_label.setText("❌ Тест не загружен!")

        self.auto_next_checkbox.setChecked(self.settings['auto_next'])
        self.font_size_spinbox.setValue(self.settings['font_size'])
        self.delay_spinbox.setValue(self.settings['delay_time'])

        self.stacked_widget.setCurrentWidget(self.settings_page)
        logger.info("Открыта страница настроек")

    def show_menu(self):
        if self.wrong_answers:
            self.menu_error_label.setText(f"⚠️ Вопросов с ошибками: {len(self.wrong_answers)}")
        else:
            self.menu_error_label.setText("✅ Нет ошибок")

        self.update_test_info()
        self.stacked_widget.setCurrentWidget(self.menu_page)
        logger.info("Открыта главная страница")

    def start_exam(self):
        logger.info("Запуск экзамена")
        self.start_test("exam")

    def start_marathon(self):
        logger.info("Запуск марафона")
        self.start_test("marathon")

    def start_errors(self):
        logger.info("Запуск повторения ошибок")
        self.start_test("errors")

    def start_test(self, mode):
        if not self.questions:
            logger.warning("Попытка запуска теста без загруженных вопросов")
            QMessageBox.critical(self, "Ошибка", "Нет загруженных вопросов!\nСначала выберите тест из меню.")
            return

        if mode == "errors" and not self.wrong_answers:
            logger.info("Нет ошибок для повторения")
            QMessageBox.information(self, "Информация", "Нет ошибок для повторения!")
            return

        self.current_mode = mode
        self.current_index = 0
        self.current_errors = 0
        self.show_results = False

        if mode == "exam":
            self.current_questions = random.sample(self.questions, min(20, len(self.questions)))
            logger.info(f"Экзамен: выбрано {len(self.current_questions)} вопросов")
        elif mode == "marathon":
            self.current_questions = self.questions.copy()
            logger.info(f"Марафон: {len(self.current_questions)} вопросов")
        elif mode == "errors":
            self.current_questions = self.wrong_answers.copy()
            logger.info(f"Повторение ошибок: {len(self.current_questions)} вопросов")

        if self.current_test_name:
            self.test_info_test_label.setText(f"Тест: {self.current_test_name}")

        self.stacked_widget.setCurrentWidget(self.test_page)
        self.show_question()

    def show_question(self):
        while self.answers_layout.count():
            item = self.answers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.answer_widgets = []

        # Создаем группу для радио-кнопок (если нужен одиночный выбор)
        self.radio_group = QButtonGroup(self.answers_frame)
        self.radio_group.setExclusive(True)  # Только один выбор

        if self.current_index >= len(self.current_questions):
            self.finish_test()
            return

        question = self.current_questions[self.current_index]

        mode_text = {
            "exam": "📝 ЭКЗАМЕН",
            "marathon": "🏃 МАРАФОН",
            "errors": "⚠️ ПОВТОРЕНИЕ ОШИБОК"
        }
        self.mode_label.setText(mode_text.get(self.current_mode, ""))

        self.question_num_label.setText(f"Вопрос {self.current_index + 1} из {len(self.current_questions)}")
        self.error_label.setText(f"Ошибок: {self.current_errors}")

        progress = int((self.current_index / len(self.current_questions)) * 100)
        self.progress_bar.setValue(progress)

        self.question_label.setText(question['question'])
        self.question_label.setWordWrap(True)
        self.question_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.is_multiple_choice = len(question["correct"]) > 1

        type_text = "Выберите ОДИН правильный ответ:" if not self.is_multiple_choice else "Выберите ВСЕ правильные ответы:"
        self.question_type_label.setText(type_text)
        self.question_type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.show_results:
            # ПОСЛЕ ОТВЕТА - показываем правильные/неправильные ответы с цветной подсветкой
            for i, answer in enumerate(question["answers"]):
                # Создаем виджет для ответа
                answer_widget = QWidget()

                # Определяем цвет в зависимости от правильности ответа
                if i in question["correct"]:
                    # Правильный ответ - зеленый
                    border_color = "#27ae60"
                    bg_color = "#e8f5e9"
                elif i in getattr(self, 'selected_indices', []):
                    # Пользователь выбрал, но это неправильно - красный
                    border_color = "#e74c3c"
                    bg_color = "#fdeaea"
                else:
                    # Невыбранный ответ - серый
                    border_color = "#ecf0f1"
                    bg_color = "white"

                answer_widget.setStyleSheet(f"""
                    QWidget {{
                        background-color: {bg_color};
                        border-radius: 8px;
                        margin: 5px;
                        padding: 15px;
                        border: 2px solid {border_color};
                    }}
                """)

                answer_layout = QHBoxLayout(answer_widget)
                answer_layout.setContentsMargins(10, 10, 10, 10)
                answer_layout.setSpacing(15)

                # Добавляем иконку только если ответ был выбран пользователем
                icon_label = QLabel()

                if i in question["correct"] and i in getattr(self, 'selected_indices', []):
                    icon_label.setText("✅")
                    icon_label.setStyleSheet("""
                        color: #27ae60; 
                        font-size: 16px;
                        padding: 5px;
                    """)
                elif i in getattr(self, 'selected_indices', []):
                    icon_label.setText("❌")
                    icon_label.setStyleSheet("""
                        color: #e74c3c; 
                        font-size: 16px;
                        padding: 5px;
                    """)
                else:
                    icon_label.setText("")
                    icon_label.setFixedWidth(30)

                answer_layout.addWidget(icon_label)

                answer_label = QLabel(answer)
                answer_label.setWordWrap(True)
                answer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                answer_label.setStyleSheet(f"""
                    color: #2c3e50; 
                    font-size: {self.settings['font_size']}px;
                    padding: 5px;
                """)
                answer_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

                answer_layout.addWidget(answer_label, 1)
                self.answers_layout.addWidget(answer_widget)
        else:
            # ДО ОТВЕТА - обычный режим выбора
            if self.is_multiple_choice:
                # Для множественного выбора - чекбоксы
                for i, answer in enumerate(question["answers"]):
                    # Создаем виджет для ответа
                    answer_widget = QWidget()
                    answer_widget.setStyleSheet("""
                        QWidget {
                            background-color: white;
                            border-radius: 8px;
                            margin: 8px;
                            padding: 15px;
                            border: 2px solid #ecf0f1;
                        }
                        QWidget:hover {
                            background-color: #f8f9fa;
                            border-color: #3498db;
                        }
                    """)

                    answer_layout = QHBoxLayout(answer_widget)
                    answer_layout.setContentsMargins(10, 10, 10, 10)
                    answer_layout.setSpacing(15)

                    checkbox = QCheckBox()
                    checkbox.setStyleSheet("""
                        QCheckBox {
                            spacing: 15px;
                        }
                        QCheckBox::indicator {
                            width: 24px;
                            height: 24px;
                            border: 2px solid #95a5a6;
                            border-radius: 4px;
                        }
                        QCheckBox::indicator:checked {
                            background-color: #3498db;
                            border-color: #2980b9;
                        }
                    """)

                    answer_label = QLabel(answer)
                    answer_label.setWordWrap(True)
                    answer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    answer_label.setStyleSheet(f"""
                        QLabel {{
                            font-size: {self.settings['font_size']}px;
                            color: #2c3e50;
                            padding: 5px;
                        }}
                    """)
                    answer_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

                    answer_layout.addWidget(checkbox)
                    answer_layout.addWidget(answer_label, 1)
                    self.answers_layout.addWidget(answer_widget)
                    self.answer_widgets.append((checkbox, answer_widget, i))

                    # Делаем кликабельной всю область виджета
                    def make_checkbox_handler(cb, widget, idx=i):
                        def handler(event):
                            cb.setChecked(not cb.isChecked())
                            self.update_widget_styles()

                        return handler

                    answer_widget.mousePressEvent = make_checkbox_handler(checkbox, answer_widget, i)
                    answer_label.mousePressEvent = make_checkbox_handler(checkbox, answer_widget, i)

            else:
                # Для одиночного выбора - радио-кнопки с группой
                for i, answer in enumerate(question["answers"]):
                    # Создаем виджет для ответа
                    answer_widget = QWidget()
                    answer_widget.setStyleSheet("""
                        QWidget {
                            background-color: white;
                            border-radius: 8px;
                            margin: 8px;
                            padding: 15px;
                            border: 2px solid #ecf0f1;
                        }
                        QWidget:hover {
                            background-color: #f8f9fa;
                            border-color: #3498db;
                        }
                    """)

                    answer_layout = QHBoxLayout(answer_widget)
                    answer_layout.setContentsMargins(10, 10, 10, 10)
                    answer_layout.setSpacing(15)

                    radio = QRadioButton()
                    radio.setStyleSheet("""
                        QRadioButton {
                            spacing: 15px;
                        }
                        QRadioButton::indicator {
                            width: 24px;
                            height: 24px;
                            border-radius: 12px;
                            border: 2px solid #95a5a6;
                        }
                        QRadioButton::indicator:checked {
                            background-color: #3498db;
                            border-color: #2980b9;
                        }
                    """)

                    answer_label = QLabel(answer)
                    answer_label.setWordWrap(True)
                    answer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    answer_label.setStyleSheet(f"""
                        QLabel {{
                            font-size: {self.settings['font_size']}px;
                            color: #2c3e50;
                            padding: 5px;
                        }}
                    """)
                    answer_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

                    answer_layout.addWidget(radio)
                    answer_layout.addWidget(answer_label, 1)
                    self.answers_layout.addWidget(answer_widget)
                    self.answer_widgets.append((radio, answer_widget, i))

                    # Добавляем радио-кнопку в группу
                    self.radio_group.addButton(radio, i)

                    # Делаем кликабельной всю область виджета и текста
                    def make_radio_handler(r, widget, idx=i):
                        def handler(event):
                            r.setChecked(True)
                            self.update_widget_styles()

                        return handler

                    answer_widget.mousePressEvent = make_radio_handler(radio, answer_widget, i)
                    answer_label.mousePressEvent = make_radio_handler(radio, answer_widget, i)

        # Устанавливаем отступы для layout ответов
        self.answers_layout.setContentsMargins(20, 10, 20, 10)

        if self.show_results:
            self.answer_button.setEnabled(False)

            if self.settings['auto_next']:
                self.next_button.hide()
                logger.debug(f"Автопереход через {self.settings['delay_time']} сек")
                QTimer.singleShot(self.settings['delay_time'] * 1000, self.next_question)
            else:
                self.next_button.setEnabled(True)
                self.next_button.show()
        else:
            self.answer_button.setEnabled(True)
            self.next_button.setEnabled(False)
            self.next_button.show()

    def update_widget_styles(self):
        """Обновить стили всех виджетов ответов"""
        for widget, answer_widget, idx in self.answer_widgets:
            if widget.isChecked():
                answer_widget.setStyleSheet("""
                    QWidget {
                        background-color: #f0f8ff;
                        border-radius: 8px;
                        margin: 8px;
                        padding: 15px;
                        border: 2px solid #3498db;
                    }
                    QWidget:hover {
                        background-color: #e0f0ff;
                    }
                """)
            else:
                answer_widget.setStyleSheet("""
                    QWidget {
                        background-color: white;
                        border-radius: 8px;
                        margin: 8px;
                        padding: 15px;
                        border: 2px solid #ecf0f1;
                    }
                    QWidget:hover {
                        background-color: #f8f9fa;
                        border-color: #3498db;
                    }
                """)

    def update_frame_styles(self):
        """Обновить стили всех фреймов ответов"""
        for widget, frame, idx in self.answer_widgets:
            if widget.isChecked():
                frame.setStyleSheet("""
                    QFrame {
                        background-color: #f0f8ff;
                        border-radius: 8px;
                        margin: 8px;
                        padding: 15px;
                        border: 2px solid #3498db;
                    }
                    QFrame:hover {
                        background-color: #e0f0ff;
                    }
                """)
            else:
                frame.setStyleSheet("""
                    QFrame {
                        background-color: white;
                        border-radius: 8px;
                        margin: 8px;
                        padding: 15px;
                        border: 2px solid #ecf0f1;
                    }
                    QFrame:hover {
                        background-color: #f8f9fa;
                        border-color: #3498db;
                    }
                """)

    def check_answer(self):
        question = self.current_questions[self.current_index]

        selected_indices = []
        if self.is_multiple_choice:
            for i, (checkbox, _, _) in enumerate(self.answer_widgets):
                if checkbox.isChecked():
                    selected_indices.append(i)
            if not selected_indices:
                QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один ответ!")
                return
        else:
            for i, (radio, _, _) in enumerate(self.answer_widgets):
                if radio.isChecked():
                    selected_indices.append(i)
                    break
            if not selected_indices:
                QMessageBox.warning(self, "Ошибка", "Выберите ответ!")
                return

        self.selected_indices = selected_indices

        is_correct = set(selected_indices) == set(question["correct"])

        if is_correct:
            self.statistics["correct"] += 1
            if self.current_mode in ["exam", "marathon"]:
                for i, wrong_q in enumerate(self.wrong_answers):
                    if wrong_q["question"] == question["question"]:
                        self.wrong_answers.pop(i)
                        logger.debug("Вопрос удален из списка ошибок")
                        break
            logger.info(f"Правильный ответ на вопрос {self.current_index + 1}")
        else:
            self.statistics["incorrect"] += 1
            self.current_errors += 1
            self.error_label.setText(f"Ошибок: {self.current_errors}")

            if question not in self.wrong_answers:
                self.wrong_answers.append(question)
                logger.debug(f"Вопрос добавлен в список ошибок: {question['question'][:50]}...")

        save_statistics(self.statistics)

        self.show_results = True
        self.show_question()

        if self.current_mode == "exam" and self.current_errors >= 3:
            logger.info(f"Экзамен не сдан. Ошибок: {self.current_errors}")
            QMessageBox.information(self, "Результат",
                                    f"Экзамен не сдан! Допущено {self.current_errors} ошибок.")
            self.show_menu()

    def next_question(self):
        self.current_index += 1
        self.show_results = False
        if hasattr(self, 'selected_indices'):
            delattr(self, 'selected_indices')
        self.show_question()

    def finish_test(self):
        if self.current_mode == "exam":
            if self.current_errors < 3:
                logger.info(f"Экзамен сдан. Ошибок: {self.current_errors}")
                QMessageBox.information(self, "Поздравляем!",
                                        f"✅ Экзамен сдан! Ошибок: {self.current_errors}")
                self.statistics["exams"] += 1
            else:
                logger.info(f"Экзамен не сдан. Ошибок: {self.current_errors}")
                QMessageBox.information(self, "Результат",
                                        f"❌ Экзамен не сдан! Ошибок: {self.current_errors}")
        elif self.current_mode == "marathon":
            logger.info(f"Марафон завершен. Вопросов: {len(self.current_questions)}")
            QMessageBox.information(self, "Результат",
                                    f"🏁 Марафон завершён! Всего вопросов: {len(self.current_questions)}")
            self.statistics["marathons"] += 1
        elif self.current_mode == "errors":
            logger.info("Повторение ошибок завершено")
            QMessageBox.information(self, "Результат",
                                    "✅ Повторение ошибок завершено!")

        save_statistics(self.statistics)
        self.show_menu()

    def show_statistics(self):
        total_answers = self.statistics["correct"] + self.statistics["incorrect"]
        accuracy = (self.statistics["correct"] / total_answers * 100) if total_answers > 0 else 0

        stats = (f"📊 СТАТИСТИКА\n\n"
                 f"📋 Текущий тест: {self.current_test_name}\n\n"
                 f"✅ Правильных ответов: {self.statistics['correct']}\n"
                 f"❌ Неправильных ответов: {self.statistics['incorrect']}\n"
                 f"🎯 Точность: {accuracy:.1f}%\n\n"
                 f"📝 Экзаменов пройдено: {self.statistics['exams']}\n"
                 f"🏃 Марафонов пройдено: {self.statistics['marathons']}\n\n"
                 f"⚠️ Вопросов с ошибками: {len(self.wrong_answers)}")

        logger.info("Показана статистика")
        QMessageBox.information(self, "Статистика", stats)


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Запуск приложения тестирования")
    logger.info(f"Базовая директория: {BASE_DIR}")
    logger.info(f"PDF OCR доступен: {PDF_OCR_AVAILABLE}")

    try:
        if sys.platform == 'darwin':
            tesseract_paths = [
                '/opt/homebrew/bin/tesseract',
                '/usr/local/bin/tesseract',
                '/opt/homebrew/opt/tesseract/bin/tesseract'
            ]
            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    logger.info(f"Найден Tesseract: {path}")
                    break
            else:
                logger.warning("Tesseract не найден. Установите: brew install tesseract")
    except:
        pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#2c3e50"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#ecf0f1"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#34495e"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2c3e50"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2c3e50"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#ecf0f1"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#ecf0f1"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#3498db"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ecf0f1"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#2980b9"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ecf0f1"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    logger.info("Окно приложения отображено")

    exit_code = app.exec()
    logger.info(f"Приложение завершено с кодом: {exit_code}")
    logger.info("=" * 50)
    sys.exit(exit_code)