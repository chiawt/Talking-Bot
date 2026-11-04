"""YouTube search links without scraping, API credentials, or downloads."""

import re
from urllib.parse import urlencode

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions


def search_url(query):
    query = ' '.join(query.split())
    if not query:
        raise ValueError('Try /play relaxing piano or /youtube chicken rice recipe.')
    if len(query) > 200:
        raise ValueError('Please shorten your search to 200 characters or fewer.')
    return query, 'https://www.youtube.com/results?' + urlencode({'search_query': query})


def text_request(text):
    """Recognize a narrow set of explicit media requests, leaving other text alone."""
    match = re.match(r'^\s*(?:play|youtube)\s+(.+)$', text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else None


async def reply_search(message, query):
    try:
        title, url = search_url(query)
    except ValueError as exc:
        await message.reply_text(str(exc))
        return
    await message.reply_text(
        f'YouTube search: {title}\nTap to choose a song or video.\n{url}',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Open YouTube', url=url)]]),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


async def youtube_command(update, context):
    from .bot import authorized
    if not await authorized(update, context):
        return
    parts = update.effective_message.text.split(maxsplit=1)
    await reply_search(update.effective_message, parts[1] if len(parts) == 2 else '')
