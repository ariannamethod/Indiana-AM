import asyncio
import logging
import re
import textwrap
from pathlib import Path

from GENESIS_orchestrator import status_emoji

# Настройка логгера
logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """Return a safe filename without path components or suspicious characters."""
    safe_name = Path(filename).name
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)
    return safe_name or "file"

def split_message(text: str, max_length: int = 4000, preserve_markdown: bool = True):
    """
    Разделяет сообщение на части, учитывая максимальную длину Telegram.
    Старается сохранять целостность абзацев и предложений.
    """
    # Если сообщение короче максимального размера, возвращаем его как есть
    if len(text) <= max_length:
        return [text]

    parts = []
    current_part = ""

    # При необходимости учитываем границы Markdown/код-блоков
    segments = (
        re.split(r"(```.*?```)", text, flags=re.DOTALL)
        if preserve_markdown
        else [text]
    )

    for segment in segments:
        if not segment:
            continue

        # Обработка код-блоков как неделимых сегментов
        if preserve_markdown and segment.startswith("```") and segment.endswith("```"):
            if len(current_part + "\n\n" + segment) > max_length and current_part:
                parts.append(current_part.strip())
                current_part = ""

            if len(segment) <= max_length:
                current_part = (
                    current_part + "\n\n" + segment if current_part else segment
                )
            else:
                # Разбиваем длинный код-блок построчно
                lines = segment.splitlines()
                fence = lines[0]
                closing = "```"
                code_lines = lines[1:-1]
                block = []
                for line in code_lines:
                    candidate = "\n".join(block + [line])
                    chunk = f"{fence}\n{candidate}\n{closing}"
                    if len(chunk) > max_length:
                        if block:
                            parts.append(f"{fence}\n{'\n'.join(block)}\n{closing}")
                            block = [line]
                        else:
                            available = max_length - len(fence) - len(closing) - 2
                            wrapped = textwrap.wrap(
                                line,
                                width=available,
                                break_long_words=False,
                                replace_whitespace=False,
                            )
                            for w in wrapped:
                                parts.append(f"{fence}\n{w}\n{closing}")
                            block = []
                    else:
                        block.append(line)
                if block:
                    parts.append(f"{fence}\n{'\n'.join(block)}\n{closing}")
                current_part = ""
        else:
            # Разбиваем длинное сообщение на части, учитывая абзацы
            paragraphs = segment.split("\n\n")
            for paragraph in paragraphs:
                if len(paragraph) > max_length:
                    sentences = paragraph.replace('. ', '.<SPLIT>').split('<SPLIT>')
                    for sentence in sentences:
                        if (
                            len(current_part + "\n\n" + sentence) > max_length
                            and current_part
                        ):
                            parts.append(current_part.strip())
                            current_part = sentence
                        else:
                            current_part = (
                                current_part + "\n\n" + sentence
                                if current_part
                                else sentence
                            )

                        if len(current_part) > max_length:
                            wrapped = textwrap.wrap(
                                current_part,
                                width=max_length,
                                break_long_words=False,
                                replace_whitespace=False,
                            )
                            parts.extend([w.strip() for w in wrapped[:-1]])
                            current_part = wrapped[-1].strip()
                else:
                    if (
                        len(current_part + "\n\n" + paragraph) > max_length
                        and current_part
                    ):
                        parts.append(current_part.strip())
                        current_part = paragraph
                    else:
                        current_part = (
                            current_part + "\n\n" + paragraph
                            if current_part
                            else paragraph
                        )

    if current_part:
        parts.append(current_part.strip())

    return parts

async def send_split_message(
    bot,
    chat_id,
    text,
    parse_mode=None,
    delay: float = 0.5,
    preserve_markdown: bool = True,
    **kwargs,
):
    """
    Отправляет сообщение в Telegram с корректным разбиением длинных сообщений.
    Добавляет индикаторы продолжения и возвращает все отправленные сообщения.

    Parameters
    ----------
    delay: float
        Задержка между отправкой частей сообщения в секундах.
    """
    # Логирование длины сообщения для отладки
    logger.info(f"Sending message with length: {len(text)} characters")

    # Проверка на обрезанное предложение
    if text and not text[-1] in ['.', '!', '?', ':', ';', '"', ')', ']', '}']:
        logger.warning("Message appears to be cut off mid-sentence")
        # Добавляем многоточие, если сообщение кажется обрезанным
        text += "..."

    parts = split_message(text, preserve_markdown=preserve_markdown)
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
                await asyncio.sleep(delay)
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
