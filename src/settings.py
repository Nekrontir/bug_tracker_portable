"""
Модуль для сохранения и загрузки настроек приложения (тема, геометрия, ширина колонок).
Файл settings.json создаётся рядом с exe/основным скриптом.
"""

import json
import os
import sys
from typing import Any, Dict


SETTINGS_FILENAME = "settings.json"


def get_app_dir() -> str:
    """
    Возвращает папку, в которой лежит исполняемый файл/основной скрипт.

    В режиме PyInstaller возвращает папку exe-файла, в обычном режиме — папку модуля.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # PyInstaller [web:239][web:242]
        return os.path.dirname(sys.executable)
    # Обычный скрипт [web:240][web:243]
    return os.path.dirname(os.path.abspath(__file__))


def get_settings_path() -> str:
    """
    Возвращает полный путь к файлу настроек settings.json рядом с приложением.
    """
    return os.path.join(get_app_dir(), SETTINGS_FILENAME)


def load_settings() -> Dict[str, Any]:
    """
    Загружает настройки из settings.json.

    Если файл не найден или повреждён, возвращает пустой словарь.
    """
    path = get_settings_path()
    if not os.path.isfile(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def save_settings(settings: Dict[str, Any]) -> None:
    """
    Сохраняет настройки в settings.json.

    При ошибке записи функция ничего не делает, чтобы не падало приложение.
    """
    path = get_settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass