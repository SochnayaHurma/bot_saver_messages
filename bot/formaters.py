from typing import TypeAlias

from aiogram import html


template = 'Имя:{name}\nСообщение:{text}\nДата:{date}'
line = '─' * 32

Message: TypeAlias = dict[str, str]


def format_messages(messages: list[Message]) -> str:
    if not messages:
        return html.bold('Сообщений пока нет :(')
    return f'\n{line}\n'.join(
        template.format(
            name=html.bold(message.get('name')),
            text=html.blockquote(message.get('message')),
            date=html.underline(message.get('date'))
        )
        for message in messages[::-1]
    )


def format_response(response: str, current_page: int, last_page: int) -> str:
    pagination_info = html.bold(f'Страница: {current_page} из {last_page}')
    return f'{response}\n{pagination_info}'
