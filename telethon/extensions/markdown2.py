#  Pyrogram - Telegram MTProto API Client Library for Python
#  Copyright (C) 2017-present Dan <https://github.com/delivrance>
#
#  This file is part of Pyrogram.
#
#  Pyrogram is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Pyrogram is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with Pyrogram.  If not, see <http://www.gnu.org/licenses/>.

# copied from pyrogram: https://github.com/KurimuzonAkuma/pyrogram

import html
import re
from struct import unpack
from typing import List, Optional, Tuple, Union
import warnings

from telethon.tl import types


class Vars:
    BOLD_DELIM = "**"
    ITALIC_DELIM = "__"
    UNDERLINE_DELIM = "--"
    STRIKE_DELIM = "~~"
    SPOILER_DELIM = "||"
    CODE_DELIM = "`"
    PRE_DELIM = "```"

    # blockquote is buggy in markdown, however html works: <blockquote expandable>
    BLOCKQUOTE_DELIM = ">>"
    BLOCKQUOTE_EXPANDABLE_DELIM = "^^"
    BLOCKQUOTE_EXPANDABLE_END_DELIM = "!^^"

    OPENING_TAG = "<{}>"
    CLOSING_TAG = "</{}>"
    URL_MARKUP = '<a href="{}">{}</a>'
    EMOJI_MARKUP = "<tg-emoji document_id={}>{}</tg-emoji>"
    FIXED_WIDTH_DELIMS = (CODE_DELIM, PRE_DELIM)

    # SMP = Supplementary Multilingual Plane: https://en.wikipedia.org/wiki/Plane_(Unicode)#Overview
    SMP_RE = re.compile(r"[\U00010000-\U0010FFFF]")
    MENTION_RE = re.compile(r"tg://user\?id=(\d+)")

    MARKDOWN_RE = re.compile(
        r"({d})|(!?)\[(.+?)\]\((.+?)\)".format(
            d="|".join(
                [
                    "".join(i)
                    for i in [
                        [rf"\{j}" for j in i]
                        for i in [
                            PRE_DELIM,
                            CODE_DELIM,
                            STRIKE_DELIM,
                            UNDERLINE_DELIM,
                            ITALIC_DELIM,
                            BOLD_DELIM,
                            SPOILER_DELIM,
                        ]
                    ]
                ]
            )
        )
    )

    @staticmethod
    def add_surrogates(text: str) -> str:
        # Replace each SMP code point with a surrogate pair
        return Vars.SMP_RE.sub(
            lambda match:  # Split SMP in two surrogates
            "".join(chr(i) for i in unpack("<HH", match.group().encode("utf-16le"))),
            text,
        )

    @staticmethod
    def remove_surrogates(text: str) -> str:
        # Replace each surrogate pair with a SMP code point
        return text.encode("utf-16", "surrogatepass").decode("utf-16")

    @staticmethod
    def replace_once(source: str, old: str, new: str, start: int):
        return source[:start] + source[start:].replace(old, new, 1)


# --------------------------- HTML -----------------------------------------------


class HTMLParserHelper(html.parser.HTMLParser):
    __slots__ = ("text", "entities", "tag_entities")

    def __init__(self):
        super().__init__()

        self.text = ""
        self.entities = []
        self.tag_entities = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        extra = {}

        if tag in ("b", "strong"):
            entity = types.MessageEntityBold
        elif tag in ("i", "em"):
            entity = types.MessageEntityItalic
        elif tag == "code":
            entity = types.MessageEntityCode
        elif tag == "pre":
            entity = types.MessageEntityPre
            extra["language"] = attrs.get("language", "")
        elif tag == "spoiler":
            entity = types.MessageEntitySpoiler
        elif tag == "a":
            url = attrs.get("href", "")
            mention = Vars.MENTION_RE.match(url)
            if mention:
                entity = types.InputMessageEntityMentionName
                extra["user_id"] = int(mention.group(1))
            else:
                entity = types.MessageEntityTextUrl
                extra["url"] = url
        elif tag == "emoji":
            entity = types.MessageEntityCustomEmoji
            custom_emoji_id = int(attrs.get("document_id"))
            extra["document_id"] = custom_emoji_id
        elif tag == "u":
            entity = types.MessageEntityUnderline
        elif tag in ("s", "del", "strike"):
            entity = types.MessageEntityStrike
        elif tag == "blockquote":
            entity = types.MessageEntityBlockquote
            extra["collapsed"] = "expandable" in attrs
        else:
            return

        if tag not in self.tag_entities:
            self.tag_entities[tag] = []

        self.tag_entities[tag].append(entity(offset=len(self.text), length=0, **extra))

    def handle_data(self, data):
        data = html.unescape(data)

        for entities in self.tag_entities.values():
            for entity in entities:
                entity.length += len(data)

        self.text += data

    def handle_endtag(self, tag):
        try:
            self.entities.append(self.tag_entities[tag].pop())
        except (KeyError, IndexError):
            line, offset = self.getpos()
            offset += 1
            warnings.warn(f"Unmatched closing tag </{tag}> at line {line}:{offset}")
        else:
            if not self.tag_entities[tag]:
                self.tag_entities.pop(tag)

    def error(self, message):
        pass


class HTMLParser:
    @staticmethod
    def parse(text: str):
        # Strip whitespaces from the beginning and the end, but preserve closing tags
        text = re.sub(r"^\s*(<[\w<>=\s\"]*>)\s*", r"\1", text)
        text = re.sub(r"\s*(</[\w</>]*>)\s*$", r"\1", text)

        parser = HTMLParserHelper()
        parser.feed(Vars.add_surrogates(text))
        parser.close()

        if parser.tag_entities:
            unclosed_tags = []

            for tag, entities in parser.tag_entities.items():
                unclosed_tags.append(f"<{tag}> (x{len(entities)})")

            warnings.warn(f"Unclosed tags: {', '.join(unclosed_tags)}")

        # Remove zero-length entities
        # entities = list(filter(lambda x: x.length > 0, parser.entities))

        ents = sorted(parser.entities, key=lambda e: e.offset) or None
        return Vars.remove_surrogates(parser.text), ents

    @staticmethod
    def unparse(text: str, entities: list) -> str:
        def parse_one(entity):
            """
            Parses a single entity and returns (start_tag, start), (end_tag, end)
            """
            entity_type = entity.type
            start = entity.offset
            end = start + entity.length

            if entity_type == types.MessageEntityBold:
                start_tag = "<b>"
                end_tag = "</b>"
            elif entity_type == types.MessageEntityItalic:
                start_tag = "<i>"
                end_tag = "</i>"
            elif entity_type == types.MessageEntityUnderline:
                start_tag = "<u>"
                end_tag = "</u>"
            elif entity_type == types.MessageEntityStrike:
                start_tag = "<s>"
                end_tag = "</s>"
            elif entity_type == types.MessageEntitySpoiler:
                start_tag = "<spoiler>"
                end_tag = "</spoiler>"
            elif entity_type == types.MessageEntityCode:
                start_tag = "<code>"
                end_tag = "</code>"
            elif entity_type == types.MessageEntityPre:
                name = "pre"
                language = getattr(entity, "language", "") or ""
                start_tag = (
                    f'<{name} language="{language}">' if language else f"<{name}>"
                )
                end_tag = f"</{name}>"
            elif entity_type == types.MessageEntityBlockquote:
                name = "blockquote"
                expandable = getattr(entity, "expandable", False)
                start_tag = f"<{name}{' expandable' if expandable else ''}>"
                end_tag = f"</{name}>"
            elif entity_type == types.MessageEntityTextUrl:
                url = entity.url
                start_tag = f'<a href="{url}">'
                end_tag = "</a>"
            elif entity_type == types.MessageEntityMentionName:
                user = entity.user
                start_tag = f'<a href="tg://user?id={user.id}">'
                end_tag = "</a>"
            elif entity_type == types.MessageEntityCustomEmoji:
                custom_emoji_id = entity.document_id
                start_tag = f'<tg-emoji document_id="{custom_emoji_id}">'
                end_tag = "</tg-emoji>"
            else:
                return

            return (start_tag, start), (end_tag, end)

        def recursive(entity_i: int) -> int:
            """
            Takes the index of the entity to start parsing from, returns the number of parsed entities inside it.
            Uses entities_offsets as a stack, pushing (start_tag, start) first, then parsing nested entities,
            and finally pushing (end_tag, end) to the stack.
            No need to sort at the end.
            """
            this = parse_one(entities[entity_i])
            if this is None:
                return 1
            (start_tag, start), (end_tag, end) = this
            entities_offsets.append((start_tag, start))
            internal_i = entity_i + 1
            # while the next entity is inside the current one, keep parsing
            while internal_i < len(entities) and entities[internal_i].offset < end:
                internal_i += recursive(internal_i)
            entities_offsets.append((end_tag, end))
            return internal_i - entity_i

        text = Vars.add_surrogates(text)

        entities_offsets = []

        # probably useless because entities are already sorted by telegram
        entities.sort(key=lambda e: (e.offset, -e.length))

        # main loop for first-level entities
        i = 0
        while i < len(entities):
            i += recursive(i)

        if entities_offsets:
            last_offset = entities_offsets[-1][1]
            # no need to sort, but still add entities starting from the end
            for entity, offset in reversed(entities_offsets):
                text = (
                    text[:offset]
                    + entity
                    + html.escape(text[offset:last_offset])
                    + text[last_offset:]
                )
                last_offset = offset

        return Vars.remove_surrogates(text)


# ---------------------------- Markdown V2 ----------------------------------------


class MarkdownV2:
    @staticmethod
    def escape_and_create_quotes(text: str, strict: bool = False):
        text_lines: List[Union[str, None]] = text.splitlines()

        # Indexes of Already escaped lines
        html_escaped_list: List[int] = []

        # Temporary Queue to hold lines to be quoted
        to_quote_list: List[Tuple[int, str]] = []

        def create_blockquote(expandable: bool = False) -> None:
            """
            Merges all lines in quote_queue into first line of queue
            Encloses that line in html quote
            Replaces rest of the lines with None placeholders to preserve indexes
            """
            if len(to_quote_list) == 0:
                return

            joined_lines = "\n".join([i[1] for i in to_quote_list])

            first_line_index, _ = to_quote_list[0]
            text_lines[first_line_index] = (
                f"<blockquote{' expandable' if expandable else ''}>{joined_lines}</blockquote>"
            )

            for line_to_remove in to_quote_list[1:]:
                text_lines[line_to_remove[0]] = None

            to_quote_list.clear()

        # Handle Expandable Quote
        inside_blockquote = False
        for index, line in enumerate(text_lines):
            if (
                line.startswith(Vars.BLOCKQUOTE_EXPANDABLE_DELIM)
                and not inside_blockquote
            ):
                delim_stripped_line = line[
                    len(Vars.BLOCKQUOTE_EXPANDABLE_DELIM)
                    + (
                        1
                        if line.startswith(f"{Vars.BLOCKQUOTE_EXPANDABLE_DELIM} ")
                        else 0
                    ) :
                ]
                parsed_line = (
                    html.escape(delim_stripped_line) if strict else delim_stripped_line
                )

                to_quote_list.append((index, parsed_line))
                html_escaped_list.append(index)

                inside_blockquote = True
                continue

            elif (
                line.endswith(Vars.BLOCKQUOTE_EXPANDABLE_END_DELIM)
                and inside_blockquote
            ):
                if line.startswith(Vars.BLOCKQUOTE_DELIM):
                    line = line[
                        len(Vars.BLOCKQUOTE_DELIM)
                        + (1 if line.startswith(f"{Vars.BLOCKQUOTE_DELIM} ") else 0) :
                    ]

                delim_stripped_line = line[: -len(Vars.BLOCKQUOTE_EXPANDABLE_END_DELIM)]

                parsed_line = (
                    html.escape(delim_stripped_line) if strict else delim_stripped_line
                )

                to_quote_list.append((index, parsed_line))
                html_escaped_list.append(index)

                inside_blockquote = False

                create_blockquote(expandable=True)

            if inside_blockquote:
                parsed_line = line[
                    len(Vars.BLOCKQUOTE_DELIM)
                    + (1 if line.startswith(f"{Vars.BLOCKQUOTE_DELIM} ") else 0) :
                ]
                parsed_line = html.escape(parsed_line) if strict else parsed_line
                to_quote_list.append((index, parsed_line))
                html_escaped_list.append(index)

        # Handle Single line/Continued Quote
        for index, line in enumerate(text_lines):
            if line is None:
                continue

            if line.startswith(Vars.BLOCKQUOTE_DELIM):
                delim_stripped_line = line[
                    len(Vars.BLOCKQUOTE_DELIM)
                    + (1 if line.startswith(f"{Vars.BLOCKQUOTE_DELIM} ") else 0) :
                ]
                parsed_line = (
                    html.escape(delim_stripped_line) if strict else delim_stripped_line
                )

                to_quote_list.append((index, parsed_line))
                html_escaped_list.append(index)

            elif len(to_quote_list) > 0:
                create_blockquote()
        else:
            create_blockquote()

        if strict:
            for idx, line in enumerate(text_lines):
                if idx not in html_escaped_list:
                    text_lines[idx] = html.escape(line)

        return "\n".join(
            [valid_line for valid_line in text_lines if valid_line is not None]
        )

    @staticmethod
    def parse(text: str, strict: bool = False):
        text = MarkdownV2.escape_and_create_quotes(text, strict=strict)
        delims = set()
        is_fixed_width = False

        for i, match in enumerate(re.finditer(Vars.MARKDOWN_RE, text)):
            start, _ = match.span()
            delim, is_emoji, text_url, url = match.groups()
            full = match.group(0)

            if delim in Vars.FIXED_WIDTH_DELIMS:
                is_fixed_width = not is_fixed_width

            if is_fixed_width and delim not in Vars.FIXED_WIDTH_DELIMS:
                continue

            if not is_emoji and text_url:
                text = Vars.replace_once(
                    text, full, Vars.URL_MARKUP.format(url, text_url), start
                )
                continue

            if is_emoji:
                emoji = text_url
                emoji_id = url.lstrip("tg://emoji?id=")
                text = Vars.replace_once(
                    text, full, Vars.EMOJI_MARKUP.format(emoji_id, emoji), start
                )
                continue

            if delim == Vars.BOLD_DELIM:
                tag = "b"
            elif delim == Vars.ITALIC_DELIM:
                tag = "i"
            elif delim == Vars.CODE_DELIM:
                tag = "code"
            elif delim == Vars.PRE_DELIM:
                tag = "pre"
            elif delim == Vars.SPOILER_DELIM:
                tag = "spoiler"
            elif delim == Vars.UNDERLINE_DELIM:
                tag = "u"
            elif delim == Vars.STRIKE_DELIM:
                tag = "s"
            else:
                continue

            if delim not in delims:
                delims.add(delim)
                tag = Vars.OPENING_TAG.format(tag)
            else:
                delims.remove(delim)
                tag = Vars.CLOSING_TAG.format(tag)

            if delim == Vars.PRE_DELIM and delim in delims:
                delim_and_language = text[text.find(Vars.PRE_DELIM) :].split("\n")[0]
                language = delim_and_language[len(Vars.PRE_DELIM) :]
                text = Vars.replace_once(
                    text, delim_and_language, f'<pre language="{language}">', start
                )
                continue

            text = Vars.replace_once(text, delim, tag, start)

        return HTMLParser.parse(text)

    @staticmethod
    def unparse(text: str, entities: list):
        text = Vars.add_surrogates(text)

        entities_offsets = []

        for entity in entities:
            entity_type = entity.type
            start = entity.offset
            end = start + entity.length

            if entity_type == types.MessageEntityBold:
                start_tag = end_tag = Vars.BOLD_DELIM
            elif entity_type == types.MessageEntityItalic:
                start_tag = end_tag = Vars.ITALIC_DELIM
            elif entity_type == types.MessageEntityUnderline:
                start_tag = end_tag = Vars.UNDERLINE_DELIM
            elif entity_type == types.MessageEntityStrike:
                start_tag = end_tag = Vars.STRIKE_DELIM
            elif entity_type == types.MessageEntityCode:
                start_tag = end_tag = Vars.CODE_DELIM
            elif entity_type == types.MessageEntityPre:
                language = getattr(entity, "language", "") or ""
                start_tag = f"{Vars.PRE_DELIM}{language}\n"
                end_tag = f"\n{Vars.PRE_DELIM}"
            elif entity_type == types.MessageEntityBlockquote:
                start_tag = Vars.BLOCKQUOTE_DELIM + " "
                end_tag = ""
                blockquote_text = text[start:end]
                lines = blockquote_text.split("\n")
                last_length = 0
                for line in lines:
                    if len(line) == 0 and last_length == end:
                        continue
                    start_offset = start + last_length
                    last_length = last_length + len(line)
                    end_offset = start_offset + last_length
                    entities_offsets.append(
                        (
                            start_tag,
                            start_offset,
                        )
                    )
                    entities_offsets.append(
                        (
                            end_tag,
                            end_offset,
                        )
                    )
                    last_length = last_length + 1
                continue
            elif entity_type == types.MessageEntitySpoiler:
                start_tag = end_tag = Vars.SPOILER_DELIM
            elif entity_type == types.MessageEntityTextUrl:
                url = entity.url
                start_tag = "["
                end_tag = f"]({url})"
            elif entity_type == types.MessageEntityMentionName:
                user = entity.user
                start_tag = "["
                end_tag = f"](tg://user?id={user.id})"
            elif entity_type == types.MessageEntityCustomEmoji:
                emoji_id = entity.custom_emoji_id
                start_tag = "!["
                end_tag = f"](tg://emoji?id={emoji_id})"
            else:
                continue

            entities_offsets.append((start_tag, start))
            entities_offsets.append((end_tag, end))

        entities_offsets = map(
            lambda x: x[1],
            sorted(
                enumerate(entities_offsets), key=lambda x: (x[1][1], x[0]), reverse=True
            ),
        )

        for entity, offset in entities_offsets:
            text = text[:offset] + entity + text[offset:]

        return Vars.remove_surrogates(text)


# --------------------------------------------------------------------------


parse = MarkdownV2.parse

from .markdown import unparse as OldUnparse

unparse = OldUnparse  # need to test new unparse func
