# meta developer: @sky_modules

from telethon.tl.types import User
from telethon.tl.functions.users import GetFullUserRequest
from .. import loader, utils


@loader.tds
class UserInfoMod(loader.Module):
    """Показывает базовую информацию о пользователе"""

    strings = {"name": "UserInfo"}

    @loader.command(
        ru_doc="[ответ/юзернейм/id] - показать информацию о пользователе",
    )
    async def whoami(self, message):
        """[reply/username/id] - show user info"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if reply:
            user = await self.client.get_entity(reply.sender_id)
        elif args:
            try:
                user = await self.client.get_entity(args)
            except Exception:
                await utils.answer(message, "❌ Пользователь не найден")
                return
        else:
            user = await self.client.get_entity(message.sender_id)

        if not isinstance(user, User):
            await utils.answer(message, "❌ Это не пользователь")
            return

        full = await self.client(GetFullUserRequest(user.id))
        bio = full.full_user.about or "—"

        text = (
            "👤 <b>Информация о пользователе</b>\n\n"
            f"<b>ID:</b> <code>{user.id}</code>\n"
            f"<b>Имя:</b> {user.first_name or '—'}\n"
            f"<b>Фамилия:</b> {user.last_name or '—'}\n"
            f"<b>Username:</b> @{user.username or '—'}\n"
            f"<b>Телефон:</b> {user.phone or '—'}\n"
            f"<b>Premium:</b> {'да' if user.premium else 'нет'}\n"
            f"<b>Бот:</b> {'да' if user.bot else 'нет'}\n"
            f"<b>Верифицирован:</b> {'да' if user.verified else 'нет'}\n"
            f"<b>Био:</b> {bio}\n"
            f"<b>Профиль:</b> <a href='tg://user?id={user.id}'>ссылка</a>"
        )

        await utils.answer(message, text)