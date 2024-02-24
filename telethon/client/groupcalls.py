import typing

from ..tl import types, functions
from .. import hints


if typing.TYPE_CHECKING:
    from .telegramclient import TelegramClient


class GroupCallMethods:
    async def create_group_call(
        self: "TelegramClient",
        peer: types.TypeInputPeer,
        rtmp_stream: typing.Optional[bool] = None,
        random_id: int = None,
        title: typing.Optional[str] = None,
        schedule_date: typing.Optional[datetime.datetime] = None,
    ):
        """
        Create or Schedule a Group Call.
        (You will need to have voice call admin previlege to start a call.)

        Args:
           peer: ChatId/Username of chat.
           rtmp_stream: Whether to start rtmp stream.
           random_id: Any random integer or leave it None.
           title: Title to keep for voice chat.
           schedule (optional): 'datetime' object to schedule call.
        """
        return await self(
            functions.phone.CreateGroupCallRequest(
                peer=peer,
                rtmp_stream=rtmp_stream,
                title=title,
                random_id=random_id,
                schedule_date=schedule_date,
            )
        )

    async def join_group_call(
        self: "TelegramClient",
        call: types.TypeInputGroupCall,
        join_as: types.TypeInputPeer,
        params: types.TypeDataJSON,
        muted: typing.Optional[bool] = None,
        video_stopped: typing.Optional[bool] = None,
        invite_hash: typing.Optional[str] = None,
    ):
        """
        Join a Group Call.

        Args:
           call:
           join_as:
           params:
           muted:
           video_stopped:
           invite_hash:
        """
        return await self(
            functions.phone.JoinGroupCallRequest(
                call=call,
                join_as=join_as,
                params=params,
                muted=muted,
                video_stopped=video_stopped,
                invite_hash=invite_hash,
            )
        )

    async def leave_group_call(
        self: "TelegramClient",
        call: types.TypeInputGroupCall,
        source: int,
    ):
        """
        Leave a Group Call.

        Args:
           call:
           source:
        """
        return await self(
            functions.phone.LeaveGroupCallRequest(call=call, source=source)
        )

    async def discard_group_call(
        self: "TelegramClient",
        call: types.TypeInputGroupCall,
    ):
        """
        Discard a Group Call.
        (You will need to have voice call admin previlege to start a call.)

        Args:
           call:
        """
        return await self(functions.phone.DiscardGroupCallRequest(call=call))

    async def get_group_call(
        self: "TelegramClient",
        call: types.TypeInputGroupCall,
        limit: int,
    ):
        """
        Get a Group Call.

        Args:
           call:
        """
        return await self(functions.phone.GetGroupCallRequest(call=call, limit=limit))
