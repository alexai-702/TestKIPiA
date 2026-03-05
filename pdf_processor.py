
import sys
import os
import re
import shutil
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QTextEdit, QProgressBar, QMessageBox, QLabel, QHBoxLayout
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt

import fitz  # PyMuPDF (необязательно, оставлено для расширения)
from PIL import Image
import pytesseract
import cv2
import numpy as np
from pdf2image import convert_from_path

# --- Настройка логирования ---
LOG_DIR = os.path.dirname(__file__) if '__file__' in globals() else os.getcwd()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'pdf_ocr_app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Если вы на Windows и tesseract не в PATH, укажите путь явно:
if sys.platform.startswith('win'):
    # Обычно: C:\Program Files\Tesseract-OCR\tesseract.exe
    default_tess = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_tess):
        pytesseract.pytesseract.tesseract_cmd = default_tess

# --- Функции поиска poppler ---
def find_poppler_path():
    """Ищет pdftoppm — сначала через PATH, затем в типичных местах."""
    binary = shutil.which('pdftoppm')
    if binary:
        return os.path.dirname(binary)

    possible_paths = [
        '/opt/homebrew/bin',
        '/usr/local/bin',
        '/opt/homebrew/opt/poppler/bin',
        '/usr/bin',
        '/usr/local/Cellar/poppler/bin'
    ]
    for path in possible_paths:
        if os.path.exists(os.path.join(path, 'pdftoppm')):
            return path
    return None

# --- Парсер вопросов из распознанного текста ---
def parse_custom_questions(text, page_num):
    """Разбирает текст в структуру вопросов/ответов."""
    questions = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        logger.warning(f"Страница {page_num}: нет текста")
        return questions

    i = 0
    q_header_re = re.compile(r'ВОПРОС\s+№\s*(\d+)', re.IGNORECASE)
    total_answers_re = re.compile(r'Всего\s+ответов:', re.IGNORECASE)
    skip_re = re.compile(r'^(Выбрано:|Из\s+них\s+правильных:)', re.IGNORECASE)
    answers_label_re = re.compile(r'Ответ(?:ь|ы)\b', re.IGNORECASE)
    next_question_re = re.compile(r'ВОПРОС\s+№\s*\d+', re.IGNORECASE)
    answer_line_re = re.compile(r'^\s*(\d+)[\.\)]\s*(.*)$')
    correct_marker_re = re.compile(r'(\*верно\*|\(верно\)|\bверно\b)', re.IGNORECASE)
    correct_cleanup_re = correct_marker_re

    while i < len(lines):
        m = q_header_re.match(lines[i])
        if not m:
            i += 1
            continue

        qnum = m.group(1)
        current_question = {
            'id': int(qnum) if qnum.isdigit() else len(questions) + 1,
            'question': '',
            'answers': [],
            'correct': [],
            'explanation': '',
            'source': f'pdf_custom_page_{page_num}'
        }
        i += 1

        # Собираем текст вопроса
        q_text_parts = []
        while i < len(lines) and not (total_answers_re.match(lines[i]) or answer_line_re.match(lines[i]) or answers_label_re.match(lines[i]) or next_question_re.match(lines[i])):
            q_text_parts.append(lines[i])
            i += 1
        current_question['question'] = ' '.join(q_text_parts).strip()

        # Пропускаем метки
        if i < len(lines) and total_answers_re.match(lines[i]):
            i += 1
        while i < len(lines) and skip_re.match(lines[i]):
            i += 1
        if i < len(lines) and answers_label_re.match(lines[i]):
            i += 1

        # Собираем ответы
        while i < len(lines):
            if next_question_re.match(lines[i]):
                break
            am = answer_line_re.match(lines[i])
            if not am:
                i += 1
                continue
            ans_num = int(am.group(1))
            ans_text = am.group(2).strip()
            # Собираем продолжения ответа (строки, не являющиеся новым ответом или заголовком)
            j = i + 1
            cont = []
            while j < len(lines) and not answer_line_re.match(lines[j]) and not next_question_re.match(lines[j]):
                cont.append(lines[j])
                j += 1
            if cont:
                ans_text = ans_text + ' ' + ' '.join(cont)
            if correct_marker_re.search(ans_text):
                current_question['correct'].append(len(current_question['answers']))
            ans_text = correct_cleanup_re.sub('', ans_text).strip()
            current_question['answers'].append(ans_text)
            i = j

        questions.append(current_question)

    return questions

# --- Класс потока для обработки PDF и OCR ---
class PDFProcessingThread(QThread):
    progress = pyqtSignal(int)
    message = pyqtSignal(str, str)  # (text, type)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, file_path, lang='rus', dpi=300, method='pdf2image', debug_save=False):
        super().__init__()
        self.file_path = file_path
        self.lang = lang
        self.dpi = dpi
        self.method = method
        self.questions = []
        self.debug_save = debug_save

    def run(self):
        try:
            logger.info(f"Обработка: {self.file_path}, метод: {self.method}")
            self.message.emit("Начинаю обработку PDF...", "info")

            if self.method == 'pdf2image':
                self.process_with_pdf2image()
            else:
                raise ValueError("Unsupported method")

            self.message.emit(f"Найдено {len(self.questions)} вопросов", "success")
            self.finished.emit(self.questions)

        except Exception as e:
            logger.exception("Ошибка в обработке PDF")
            self.error.emit(str(e))
            self.message.emit(f"Ошибка: {str(e)}", "error")

    def process_with_pdf2image(self):
        poppler_path = find_poppler_path()
        if not poppler_path:
            raise Exception("Poppler (pdftoppm) не найден. Установите poppler и убедитесь, что pdftoppm доступен.")

        try:
            images = convert_from_path(self.file_path, dpi=self.dpi, poppler_path=poppler_path)
        except Exception as e:
            logger.exception("Ошибка конвертации PDF")
            raise

        total = len(images)
        for idx, image in enumerate(images):
            self.progress.emit(int((idx + 1) / total * 100))
            self.message.emit(f"Страница {idx+1}/{total}: предобработка...", "info")

            pil_for_tess = self.preprocess_image(image)

            # отладка: сохранить изображение, которое идёт в Tesseract
            if self.debug_save:
                debug_name = os.path.join(LOG_DIR, f"debug_page_{idx+1}.png")
                pil_for_tess.save(debug_name)
                logger.info(f"Debug: saved {debug_name}")

            # OCR
            self.message.emit(f"Страница {idx+1}: распознавание...", "info")
            try:
                text = pytesseract.image_to_string(pil_for_tess, lang=self.lang)
            except Exception as e:
                logger.exception("Ошибка в pytesseract")
                text = ""

            logger.debug(f"OCR page {idx+1} first 300 chars: {text[:300]!r}")

            # Парсинг вопросов
            page_questions = parse_custom_questions(text, idx + 1)
            self.questions.extend(page_questions)

    def preprocess_image(self, image):
        """Улучшение изображения для OCR. Возвращает PIL.Image RGB."""
        # image — PIL.Image в RGB
        arr = np.array(image)  # RGB
        img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        # Серая шкала
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Увеличение для мелкого шрифта
        scale = 2.0
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Удаление шума
        gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # Контраст и порог — пробуем adaptive если OTSU слишком агрессивен
        try:
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        except Exception:
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 11, 2)

        # Конвертируем обратно в PIL RGB
        pil_img = Image.fromarray(thresh).convert("RGB")
        return pil_img

# --- Простой GUI для запуска ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF OCR Parser")
        self.resize(800, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        hl = QHBoxLayout()
        self.file_label = QLabel("Файл: не выбран")
        btn_open = QPushButton("Открыть PDF")
        btn_open.clicked.connect(self.open_file)
        hl.addWidget(self.file_label)
        hl.addWidget(btn_open)
        layout.addLayout(hl)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.start_btn = QPushButton("Запустить OCR")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_processing)
        layout.addWidget(self.start_btn)

        self.file_path = None
        self.thread = None

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите PDF", "", "PDF Files (*.pdf)")
        if path:
            self.file_path = path
            self.file_label.setText(f"Файл: {os.path.basename(path)}")
            self.start_btn.setEnabled(True)

    def append_log(self, text, level='info'):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {text}")

    def start_processing(self):
        if not self.file_path:
            QMessageBox.warning(self, "Ошибка", "Файл не выбран")
            return

        # Проверьте Tesseract и языковые файлы отдельно при необходимости
        self.thread = PDFProcessingThread(self.file_path, lang='rus', dpi=300, method='pdf2image', debug_save=True)
        self.thread.progress.connect(self.progress.setValue)
        self.thread.message.connect(self.on_message)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.start_btn.setEnabled(False)
        self.thread.start()

    def on_message(self, text, typ):
        self.append_log(text)

    def on_finished(self, questions):
        self.append_log(f"Готово. Вопросов: {len(questions)}")
        # Для примера — вывести первые пару вопросов
        for q in questions[:10]:
            self.append_log(f"Q{q['id']}: {q['question']}")
            for idx, a in enumerate(q['answers']):
                mark = "(OK)" if idx in q['correct'] else ""
                self.append_log(f"  {idx+1}. {a} {mark}")
        self.start_btn.setEnabled(True)

    def on_error(self, msg):
        self.append_log(f"Ошибка: {msg}")
        QMessageBox.critical(self, "Ошибка", msg)
        self.start_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
