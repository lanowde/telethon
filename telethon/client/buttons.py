import typing

from .. import utils, hints
from ..tl import types, custom


class ButtonMethods:
    @staticmethod
    def build_reply_markup(
        buttons: "typing.Optional[hints.MarkupLike]",
    ) -> "typing.Optional[types.TypeReplyMarkup]":
        """
        Builds a :tl:`ReplyInlineMarkup` or :tl:`ReplyKeyboardMarkup` for
        the given buttons.

        Does nothing if either no buttons are provided or the provided
        argument is already a reply markup.

        You should consider using this method if you are going to reuse
        the markup very often. Otherwise, it is not necessary.

        This method is **not** asynchronous (don't use ``await`` on it).

        Arguments
            buttons (`hints.MarkupLike`):
                The button, list of buttons, array of buttons or markup
                to convert into a markup.

        Example
            .. code-block:: python

                from telethon import Button

                markup = client.build_reply_markup(Button.inline('hi'))
                # later
                await client.send_message(chat, 'click me', buttons=markup)
        """
        if buttons is None:
            return None

        try:
            if buttons.SUBCLASS_OF_ID == 0xE2E10EF2:
                return buttons  # crc32(b'ReplyMarkup'):
        except AttributeError:
            pass

        if not utils.is_list_like(buttons):
            buttons = [[buttons]]
        elif not buttons or not utils.is_list_like(buttons[0]):
            buttons = [buttons]

        is_inline = False
        is_normal = False
        resize = None
        single_use = None
        selective = None
        persistent = None
        placeholder = None

        rows = []
        for row in buttons:
            current = []
            for button in row:
                if isinstance(button, custom.Button):
                    if button.resize is not None:
                        resize = button.resize
                    if button.single_use is not None:
                        single_use = button.single_use
                    if button.selective is not None:
                        selective = button.selective
                    if button.persistent is not None:
                        persistent = button.persistent
                    if button.placeholder is not None:
                        placeholder = button.placeholder

                    button = button.button
                elif isinstance(button, custom.MessageButton):
                    button = button.button

                inline = custom.Button._is_inline(button)
                is_inline |= inline
                is_normal |= not inline

                if button.SUBCLASS_OF_ID == 0xBAD74A3:
                    # 0xbad74a3 == crc32(b'KeyboardButton')
                    current.append(button)

            if current:
                rows.append(types.KeyboardButtonRow(current))

        if is_inline and is_normal:
            raise ValueError("You cannot mix inline with normal buttons")
        elif is_inline:
            return types.ReplyInlineMarkup(rows)

        return types.ReplyKeyboardMarkup(
            rows,
            resize=resize,
            single_use=single_use,
            selective=selective,
            persistent=persistent,
            placeholder=placeholder,
        )
