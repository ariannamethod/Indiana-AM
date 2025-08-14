import asyncio
import logging
import re
from pathlib import Path

from GENESIS_orchestrator import status_emoji

# Настройка логгера
logger = logging.getLogger(__name__)


def run_background(coro):
    """Run ``coro`` in the background and log exceptions."""
    task = asyncio.create_task(coro)

    def _log_exception(t: asyncio.Task):
        if t.cancelled():
            return
        exc = t.exception()
        if exc:
            logger.error("Background task failed", exc_info=exc)

    task.add_done_callback(_log_exception)
    return task


def sanitize_filename(filename: str) -> str:
    """Return a safe filename without path components or suspicious characters."""
    safe_name = Path(filename).name
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)
    return safe_name or "file"

def split_message(text: str, max_length: int = 4000):
    """
    Разделяет сообщение на части, учитывая максимальную длину Telegram.
    Старается сохранять целостность абзацев и предложений.
    """
    # Если сообщение короче максимального размера, возвращаем его как есть
    if len(text) <= max_length:
        return [text]

    parts = []
    current_part = ""

    # Разбиваем длинное сообщение на части, учитывая абзацы
    paragraphs = text.split('\n\n')

    for paragraph in paragraphs:
        # Если абзац сам по себе длиннее максимального размера, его нужно разбить по предложениям
        if len(paragraph) > max_length:
            sentences = paragraph.replace('. ', '.<SPLIT>').split('<SPLIT>')
            for sentence in sentences:
                if len(current_part + "\n\n" + sentence) > max_length and current_part:
                    parts.append(current_part.strip())
                    current_part = sentence
                else:
                    if current_part:
                        current_part += "\n\n" + sentence
                    else:
                        current_part = sentence

                # Проверяем не превышает ли текущая часть с одним предложением максимальную длину
                if len(current_part) > max_length:
                    # Если предложение длиннее максимума, разбиваем по словам
                    while len(current_part) > max_length:
                        cut = current_part.rfind(" ", 0, max_length)
                        if cut < 0:
                            cut = max_length
                        parts.append(current_part[:cut].strip())
                        current_part = current_part[cut:].strip()
        else:
            # Если с этим абзацем сообщение станет слишком длинным, начинаем новую часть
            if len(current_part + "\n\n" + paragraph) > max_length and current_part:
                parts.append(current_part.strip())
                current_part = paragraph
            else:
                if current_part:
                    current_part += "\n\n" + paragraph
                else:
                    current_part = paragraph

    # Добавляем последнюю часть, если она не пустая
    if current_part:
        parts.append(current_part.strip())

    return parts

async def send_split_message(bot, chat_id, text, parse_mode=None, **kwargs):
    """
    Отправляет сообщение в Telegram с корректным разбиением длинных сообщений.
    Добавляет индикаторы продолжения и возвращает все отправленные сообщения.
    """
    # Логирование длины сообщения для отладки
    logger.info(f"Sending message with length: {len(text)} characters")

    # Проверка на обрезанное предложение
    if text and not text[-1] in ['.', '!', '?', ':', ';', '"', ')', ']', '}']:
        logger.warning("Message appears to be cut off mid-sentence")
        # Добавляем многоточие, если сообщение кажется обрезанным
        text += "..."

    parts = split_message(text)
    sent_messages = []

    logger.info(f"Split into {len(parts)} parts")

    for i, part in enumerate(parts):
        # Добавляем эмодзи-индикатор и статус для первой части ответа
        if i == 0:
            part = f"☝🏻{status_emoji()} " + part.lstrip()

        # Добавляем индикатор продолжения/окончания сообщения
        if i < len(parts) - 1:
            part += "\n\n[продолжение следует...]"

        try:
            sent = await bot.send_message(chat_id=chat_id, text=part, parse_mode=parse_mode, **kwargs)
            sent_messages.append(sent)

            # Небольшая задержка между сообщениями для лучшего восприятия
            if i < len(parts) - 1:
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error sending message part {i+1}/{len(parts)}: {str(e)}")
            # Попытаемся отправить сообщение об ошибке
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ Возникла ошибка при отправке части сообщения: {str(e)}"
                )
            except Exception:
                pass

    return sent_messages[0] if len(sent_messages) == 1 else sent_messages
