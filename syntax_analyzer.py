# --- START OF FILE syntax_analyzer.py ---

import os
import sys
from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener
from antlr4.ParserRuleContext import ParserRuleContext

# Предполагаем, что генерация ANTLR прошла успешно
# Убедитесь, что папка 'gen' существует и содержит эти файлы
# Correct import structure for generated files if they are in 'gen' directory
# (assuming syntax_analyzer.py is at the same level as 'gen')
from gen.ListLangLexer import ListLangLexer
from gen.ListLangParser import ListLangParser
# ListLangListener is not directly used for syntax errors, but kept for consistency
from gen.ListLangListener import ListLangListener

# Import Semantic Analyzer components
from semantic_analyzer import perform_semantic_analysis

# НОВЫЙ ИМПОРТ: Импортируем функцию компилятора
from wat_compiler import compile_listlang_to_wat


# --- Кастомный слушатель ошибок для ANTLR парсера ---
# Этот класс перехватывает ошибки, которые генерирует парсер ANTLR,
# и передает их в наш SyntaxErrorReporter, чтобы он мог их собрать и вывести.
class CustomSyntaxErrorListener(ErrorListener):
    def __init__(self, syntax_reporter_instance):
        super().__init__()
        self.syntax_reporter = syntax_reporter_instance

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        # ANTLR передает много информации, мы используем ее для форматирования сообщения об ошибке
        # offendingSymbol.text может быть None для некоторых ошибок, поэтому добавим проверку
        symbol_text = offendingSymbol.text if offendingSymbol else "<unknown_symbol>"
        error_message = f"Ошибка синтаксиса: '{symbol_text}' на строке {line}, столбце {column} - {msg}"
        self.syntax_reporter.report_error(error_message)


# --- Основной синтаксический анализатор (только для сбора ошибок синтаксиса) ---
class SyntaxErrorReporter:
    def __init__(self, filename="<unknown>"):
        self.filename = filename
        self.errors = []  # Список для сбора синтаксических ошибок

    def report_error(self, error_message):
        """Метод для сообщения об ошибках из CustomSyntaxErrorListener."""
        full_error_message = f"[{self.filename}] {error_message}"
        if full_error_message not in self.errors:  # Avoid duplicate reporting for same error
            self.errors.append(full_error_message)
            # print(full_error_message, file=sys.stderr) # Optionally print immediately


# --- Вспомогательные функции ---

def read_code(file_path):
    """
    Читает код из файла с кодировкой UTF-8.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        print(f"Ошибка чтения файла {file_path}: Неверная кодировка, ожидается UTF-8.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Ошибка чтения файла {file_path}: {e}", file=sys.stderr)
        return None


def create_token_stream(code):
    """
    Создает поток токенов из строкового кода.
    """
    input_stream = InputStream(code)
    lexer = ListLangLexer(input_stream)
    return CommonTokenStream(lexer)


def create_parser(token_stream):
    """
    Создает парсер и настраивает его для пользовательской обработки ошибок.
    """
    parser = ListLangParser(token_stream)
    parser.removeErrorListeners()  # Удаляем стандартный ConsoleErrorListener
    return parser


def create_parse_tree(parser):
    """
    Пытается построить дерево разбора.
    """
    return parser.program()


def main_analyzer(file_path):
    """Основная функция для выполнения синтаксического и семантического анализа одного файла"""
    filename = os.path.basename(file_path)
    print(f"\n======== Анализ файла: {filename} ========")

    # Чтение кода из файла
    code = read_code(file_path)
    if code is None:
        print(f"[{filename}] Анализ отменен из-за ошибки чтения файла.", file=sys.stderr)
        return

    # Создание токенов и парсера
    token_stream = create_token_stream(code)
    parser = create_parser(token_stream)

    # Настройка слушателя синтаксических ошибок
    syntax_error_reporter = SyntaxErrorReporter(filename)
    custom_error_listener = CustomSyntaxErrorListener(syntax_error_reporter)
    parser.addErrorListener(custom_error_listener)

    parse_tree = None
    try:
        # --- Синтаксический анализ ---
        print(f"[{filename}] --- Начало синтаксического анализа ---")
        parse_tree = create_parse_tree(parser)

        syntax_errors_count = len(syntax_error_reporter.errors)
        if syntax_errors_count > 0:
            print(f"[{filename}] Синтаксический анализ завершен с {syntax_errors_count} ошибками.")
            print(f"[{filename}] Найденные синтаксические ошибки:")
            for err in syntax_error_reporter.errors:
                print(f"  {err}")
        else:
            print(f"[{filename}] Синтаксический анализ успешно завершен. Ошибок не найдено.")

        # --- Семантический анализ (всегда запускается) ---
        print(f"\n[{filename}] --- Переход к семантическому анализу ---")
        semantic_analyzer_instance = perform_semantic_analysis(parse_tree, parser, filename)

        if semantic_analyzer_instance and semantic_analyzer_instance.errors:
            print(f"[{filename}] Семантический анализ завершен с {len(semantic_analyzer_instance.errors)} ошибками.")
            # Ошибки уже выведены самим SemanticAnalyzer
            print(f"[{filename}] Кодогенерация пропущена из-за семантических ошибок.")
        else:
            print(f"[{filename}] Семантический анализ успешно завершен. Ошибок не обнаружено.")

            # --- Кодогенерация ---
            print(f"\n[{filename}] --- Начало кодогенерации (WAT) ---")
            wat_output = compile_listlang_to_wat(parse_tree, parser, semantic_analyzer_instance, filename)

            # Сохраняем WAT-код в файл
            output_wat_path = os.path.join(os.path.dirname(file_path), filename.replace('.txt', '.wat'))
            with open(output_wat_path, 'w', encoding='utf-8') as f:
                f.write(wat_output)
            print(f"[{filename}] Кодогенерация завершена. Вывод сохранен в {output_wat_path}")

    except Exception as e:
        print(f"[{filename}] Критическая ошибка во время анализа: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

    print(f"======== Завершение анализа файла: {filename} ========\n")



# --- Точка входа в программу ---
if __name__ == '__main__':
    examples_dir = os.path.dirname(os.path.abspath(__file__))

    example_files = [
        "example_1.txt",
        "example_2.txt",
        "example_3.txt",
        "add_example_4.txt",
        "new_errors.txt",
    ]

    for filename in example_files:
        file_path = os.path.join(examples_dir, filename)
        main_analyzer(file_path)