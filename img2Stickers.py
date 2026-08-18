# meta developer: @sky_modules

import io
import re
import random
import string
import asyncio
from PIL import Image
from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class Img2StickerMod(loader.Module):
    """Делает стикер из картинки (реплаем), при необходимости создаёт стикерпак и добавляет туда стикер"""

    strings = {
        "name": "Img2Sticker",
        "no_reply": "🚫 <b>Ответь на сообщение с картинкой</b>",
        "no_photo": "🚫 <b>В сообщении нет изображения</b>",
        "processing": "🔄 <b>Обрабатываю изображение...</b>",
        "trying_add": "📦 <b>Пробую добавить в существующий пак...</b>",
        "creating": "🆕 <b>Пак не найден, создаю новый...</b>",
        "done": "✅ <b>Готово! Пак:</b> https://t.me/addstickers/{}",
        "error": "🚫 <b>Ошибка:</b> {}",
        "timeout": "🚫 <b>Stickers бот не ответил вовремя</b>",
    }

    async def client_ready(self, client, db):
        self.client = client

    def _to_sticker_bytes(self, raw: bytes) -> io.BytesIO:
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        w, h = img.size
        scale = 512 / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        offset = ((512 - new_w) // 2, (512 - new_h) // 2)
        canvas.paste(img, offset, img)

        out = io.BytesIO()
        canvas.save(out, format="PNG")
        out.name = "sticker.png"
        out.seek(0)
        return out

    def _sanitize_short_name(self, raw: str) -> str:
        name = re.sub(r"[^a-zA-Z0-9_]", "_", raw.strip())
        if not name or not name[0].isalpha():
            name = "pack_" + name
        name = name.strip("_")[:40] or "pack"
        suffix = "".join(random.choices(string.digits, k=4))
        return f"{name}_{suffix}"

    async def _fresh_sticker_file(self, reply):
        raw = await reply.download_media(bytes)
        return self._to_sticker_bytes(raw)

    @loader.command()
    async def s2pcmd(self, message: Message):
        """<название/short_name пака> - сделать стикер из картинки (реплай), добавить в пак, а если пака нет - создать его"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if not reply:
            await utils.answer(message, self.strings("no_reply"))
            return

        if not reply.photo and not (reply.document and "image" in (reply.document.mime_type or "")):
            await utils.answer(message, self.strings("no_photo"))
            return

        if not args:
            args = "My Stickers"

        pack_name = (
            args.strip().split("?")[0].rstrip("/").split("/")[-1].lstrip("@")
        )

        await utils.answer(message, self.strings("processing"))

        try:
            async with self.client.conversation("Stickers", exclusive=False, timeout=25) as conv:

                await utils.answer(message, self.strings("trying_add"))

                await conv.send_message("/addsticker")
                await conv.get_response()

                await conv.send_message(pack_name)
                resp = await conv.get_response()
                low = resp.raw_text.lower()

                if "invalid set" in low or "no stickerpack" in low:
                    # пака не существует - создаём новый
                    await conv.send_message("/cancel")
                    await conv.get_response()

                    await utils.answer(message, self.strings("creating"))

                    short_name = self._sanitize_short_name(pack_name)
                    title = args.strip()[:64] or "My Stickers"

                    await conv.send_message("/newpack")
                    await conv.get_response()

                    await conv.send_message(title)
                    resp2 = await conv.get_response()

                    if "send me the sticker" not in resp2.raw_text.lower() and "png or a tgs" not in resp2.raw_text.lower() and "send me a picture" not in resp2.raw_text.lower():
                        await utils.answer(
                            message,
                            self.strings("error").format(
                                f"На этапе названия бот ответил:\n{utils.escape_html(resp2.raw_text)}"
                            ),
                        )
                        return

                    sticker_file = await self._fresh_sticker_file(reply)
                    await conv.send_file(sticker_file, force_document=True)
                    resp3 = await conv.get_response()

                    if "emoji" not in resp3.raw_text.lower() and "please" not in resp3.raw_text.lower():
                        await utils.answer(
                            message,
                            self.strings("error").format(
                                f"На этапе отправки картинки бот ответил:\n{utils.escape_html(resp3.raw_text)}"
                            ),
                        )
                        return

                    await conv.send_message("😀")
                    await conv.get_response()

                    await conv.send_message("/publish")
                    resp4 = await conv.get_response()

                    # бот может пройти несколько промежуточных шагов подряд
                    # (иконка пака, запрос short name и т.д.) - обрабатываем их по очереди
                    final = resp4
                    for _ in range(4):
                        low4 = final.raw_text.lower()

                        if "t.me/addstickers/" in final.raw_text:
                            break

                        if "icon" in low4 or "100x100" in low4:
                            await conv.send_message("/skip")
                            final = await conv.get_response()
                            continue

                        if "short name" in low4 or "come up" in low4 or (
                            "link" in low4 and "http" not in low4
                        ):
                            await conv.send_message(short_name)
                            final = await conv.get_response()
                            continue

                        # неизвестный промежуточный шаг - прекращаем и показываем ответ
                        break

                    match = re.search(r"t\.me/addstickers/(\w+)", final.raw_text)
                    if match:
                        final_name = match.group(1)
                        await utils.answer(message, self.strings("done").format(final_name))
                    else:
                        await utils.answer(
                            message,
                            self.strings("error").format(
                                f"Не удалось распознать ссылку, ответ бота:\n{utils.escape_html(final.raw_text)}"
                            ),
                        )
                    return

                # пак существует - добавляем стикер как обычно
                if "please send me the sticker" not in low and "send me a sticker" not in low:
                    await utils.answer(
                        message,
                        self.strings("error").format(utils.escape_html(resp.raw_text)),
                    )
                    return

                sticker_file = await self._fresh_sticker_file(reply)
                await conv.send_file(sticker_file, force_document=True)
                await conv.get_response()

                await conv.send_message("😀")
                await conv.get_response()

                await conv.send_message("/done")
                await conv.get_response()

                await utils.answer(message, self.strings("done").format(pack_name))

        except asyncio.TimeoutError:
            await utils.answer(message, self.strings("timeout"))
        except Exception as e:
            await utils.answer(message, self.strings("error").format(utils.escape_html(str(e))))
