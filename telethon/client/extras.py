import asyncio
import typing

from ..tl import types, functions
from .. import utils, hints, events


if typing.TYPE_CHECKING:
    from .telegramclient import TelegramClient


class ExtraMethods:
    async def transcribe(
        self: "TelegramClient",
        peer: "hints.EntityLike",
        message: "hints.MessageIDLike",
        timeout: int = 30,
    ) -> typing.Optional[str]:
        result = await self(
            functions.messages.TranscribeAudioRequest(
                peer,
                utils.get_message_id(message),
            )
        )
    
        transcription_result = None
    
        event = asyncio.Event()
    
        @self.on(events.Raw(types.UpdateTranscribedAudio))
        async def handler(update):
            nonlocal result, transcription_result
            if update.transcription_id != result.transcription_id or update.pending:
                return
    
            transcription_result = update.text
            event.set()
            raise events.StopPropagation
    
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except Exception:
            return None
    
        return transcription_result
    
    async def set_emoji_status(
        self: "TelegramClient",
        document_id: int,
        until: typing.Optional[int] = None,
    ) -> bool:
        return await self(
            functions.account.UpdateEmojiStatusRequest(
                types.EmojiStatusUntil(document_id, until)
                if until
                else types.EmojiStatus(document_id)
            )
        )
    
    async def join_chat(
        self: "TelegramClient",
        entity: types.InputChannel = None,
        hash: str = "",
    ):
        if entity:
            return await self(functions.channels.JoinChannelRequest(entity))
        elif hash:
            return await self(functions.messages.ImportChatInviteRequest(hash))
        raise ValueError("Either entity or hash is required.")
    
    
    async def hide_participants(
        self: "TelegramClient",
        channel: types.InputChannel,
        enabled: bool = False,
    ):
        """Toggle hidden participants"""
        return await self(
            functions.channels.ToggleParticipantsHiddenRequest(channel, enabled)
        )
    
    async def set_contact_photo(
        self: "TelegramClient",
        user: types.InputUser,
        file: str = None,
        video: str = None,
        suggest: bool = True,
        save: bool = False,
        **kwargs,
    ):
        if isinstance(file, str):
            file = await self.upload_file(file)
            video = None
        elif isinstance(video, str):
            video = await self.upload_file(video)
            file = None
        return await self(
            functions.photos.UploadContactProfilePhotoRequest(
                user,
                file=file,
                video=video,
                suggest=suggest,
                save=True,
                **kwargs,
            )
        )
    