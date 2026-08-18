# meta developer: @sky_modules

from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class NotesMod(loader.Module):
    """Модуль для заметок"""

    strings = {"name": "SNotes"}

    async def client_ready(self, client, db):
        self._db = db
        self.notes = self._db.get("Notes", "notes", {})

    def _save(self):
        self._db.set("Notes", "notes", self.notes)

    @loader.command(
        ru_doc="<название> (ответом на сообщение) - сохранить заметку",
    )
    async def savenote(self, message):
        """<name> (as reply) - save a note"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if not args:
            await utils.answer(message, "❌ Укажи название заметки: <code>.savenote название</code>")
            return

        if not reply or not reply.text:
            await utils.answer(message, "❌ Ответь этой командой на сообщение с текстом заметки")
            return

        name = args.strip().lower()
        self.notes[name] = reply.text
        self._save()

        await utils.answer(message, f"✅ Заметка <b>{utils.escape_html(name)}</b> сохранена")

    @loader.command(
        ru_doc="показать все заметки",
    )
    async def notes_cmd(self, message):
        """show all notes"""
        if not self.notes:
            await utils.answer(message, "📭 Заметок пока нет")
            return

        text = "📝 <b>Список заметок:</b>\n\n"
        for name in sorted(self.notes.keys()):
            preview = self.notes[name]
            if len(preview) > 50:
                preview = preview[:50] + "…"
            text += f"▫️ <code>{utils.escape_html(name)}</code> — {utils.escape_html(preview)}\n"

        await utils.answer(message, text)

    @loader.command(
        ru_doc="<название> - показать конкретную заметку",
    )
    async def note(self, message):
        """<name> - show a specific note"""
        args = utils.get_args_raw(message)

        if not args:
            await utils.answer(message, "❌ Укажи название заметки: <code>.note название</code>")
            return

        name = args.strip().lower()

        if name not in self.notes:
            await utils.answer(message, f"❌ Заметка <b>{utils.escape_html(name)}</b> не найдена")
            return

        await utils.answer(
            message,
            f"📝 <b>{utils.escape_html(name)}</b>\n\n{utils.escape_html(self.notes[name])}",
        )

    @loader.command(
        ru_doc="<название> - удалить заметку",
    )
    async def delnote(self, message):
        """<name> - delete a note"""
        args = utils.get_args_raw(message)

        if not args:
            await utils.answer(message, "❌ Укажи название заметки: <code>.delnote название</code>")
            return

        name = args.strip().lower()

        if name not in self.notes:
            await utils.answer(message, f"❌ Заметка <b>{utils.escape_html(name)}</b> не найдена")
            return

        del self.notes[name]
        self._save()

        await utils.answer(message, f"🗑 Заметка <b>{utils.escape_html(name)}</b> удалена")
