# meta developer: @sky_modules

from collections import Counter
from datetime import datetime

from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class StatMod(loader.Module):
    """Статистика сообщений в чате"""

    strings = {"name": "Stat"}

    async def client_ready(self, client, db):
        self._db = db
        self._client = client
        # {chat_id: {"date": "YYYY-MM-DD", "users": {user_id: count}, "names": {user_id: name}}}
        self.stats = self._db.get("Stat", "stats", {})

    def _save(self):
        self._db.set("Stat", "stats", self.stats)

    def _today(self):
        return datetime.now().strftime("%Y-%m-%d")

    async def watcher(self, message: Message):
        if not isinstance(message, Message):
            return
        if not message.chat_id or not message.sender_id:
            return
        if message.out:
            return

        chat_id = str(message.chat_id)
        today = self._today()

        chat_stats = self.stats.get(chat_id)
        if not chat_stats or chat_stats.get("date") != today:
            chat_stats = {"date": today, "users": {}, "names": {}}

        user_id = str(message.sender_id)
        chat_stats["users"][user_id] = chat_stats["users"].get(user_id, 0) + 1

        if user_id not in chat_stats["names"]:
            sender = await message.get_sender()
            if sender:
                name = utils.get_display_name(sender) or str(user_id)
            else:
                name = str(user_id)
            chat_stats["names"][user_id] = name

        self.stats[chat_id] = chat_stats
        self._save()

    @loader.command(
        ru_doc="показать статистику сообщений в чате за сегодня",
    )
    async def stat(self, message):
        """show today's message stats in this chat"""
        chat_id = str(message.chat_id)
        today = self._today()

        chat_stats = self.stats.get(chat_id)
        if not chat_stats or chat_stats.get("date") != today or not chat_stats["users"]:
            await utils.answer(message, "📭 За сегодня в этом чате пока нет статистики")
            return

        counter = Counter(chat_stats["users"])
        top = counter.most_common(15)
        total = sum(counter.values())

        text = f"📊 <b>Статистика чата за сегодня</b>\n\n"
        medals = ["🥇", "🥈", "🥉"]

        for i, (user_id, count) in enumerate(top):
            name = chat_stats["names"].get(user_id, user_id)
            prefix = medals[i] if i < 3 else f"{i + 1}."
            text += f"{prefix} {utils.escape_html(name)} — <b>{count}</b>\n"

        text += f"\nВсего сообщений: <b>{total}</b>"

        await utils.answer(message, text)

    @loader.command(
        ru_doc="сбросить статистику в этом чате",
    )
    async def statreset(self, message):
        """reset stats for this chat"""
        chat_id = str(message.chat_id)

        if chat_id in self.stats:
            del self.stats[chat_id]
            self._save()
            await utils.answer(message, "🗑 Статистика этого чата сброшена")
        else:
            await utils.answer(message, "📭 Статистики для этого чата и так нет")
