# GNU V3
# https://github.com/New-dev0/Telethon-Patch

from ..tl import types
from ..tl.functions.phone import ToggleGroupCallRecordRequest
from .common import EventCommon, name_inner_event, EventBuilder


@name_inner_event
class GroupCall(EventBuilder):
    """
    Occurs on certain event like

    * Group call started
    * Group call ended
    * Group call scheduled
    """

    @classmethod
    def build(cls, update, _, __):
        if isinstance(
            update, (types.UpdateNewMessage, types.UpdateNewChannelMessage)
        ) and isinstance(update.message, types.MessageService):
            update = update.message
            if isinstance(update.action, types.MessageActionGroupCall):
                return cls.Event(update, duration=update.action.duration or 0)
            elif isinstance(update.action, types.MessageActionGroupCallScheduled):
                return cls.Event(update, scheduled=True)

    class Event(EventCommon):
        def __init__(self, update, scheduled=None, duration=None):
            super().__init__(update.peer_id, update.id)
            self._update = update
            self._input_call = update.action.call
            self._scheduled = scheduled
            self.duration = duration
            self.started = None
            self.ended = None

            if duration == 0:
                self.started = True
            elif duration != None:
                self.ended = True

        @property
        def input_call(self):
            """returns 'InputGroupCall'"""
            return self._input_call

        @property
        def scheduled(self):
            """Whether Group call has been scheduled."""
            return self._scheduled

        async def start(self, *args, **kwargs):
            """Start Group call."""
            return await self.client.create_group_call(self.chat_id, *args, **kwargs)

        async def discard(self):
            """End Group call."""
            return await self.client.discard_group_call(self.input_call)

        async def toggle_record(
            self, start=None, video=None, video_portrait=None, title=None
        ):
            """Toggle group call record."""
            if self.client:
                return await self.client(
                    ToggleGroupCallRecordRequest(
                        self.input_call,
                        start=start,
                        video=video,
                        video_portrait=video_portrait,
                        title=title,
                    )
                )
