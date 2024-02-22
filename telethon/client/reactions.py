import typing

from ..tl import types, functions
from .. import utils, hints


if typing.TYPE_CHECKING:
    from .telegramclient import TelegramClient


class ReactionMethods:
    async def send_reaction(
        self: "TelegramClient",
        entity: "hints.DialogLike",
        msg_id: "hints.MessageIDLike",
        reaction: "typing.Optional[hints.Reaction]" = None,
        big: bool = False,
        add_to_recent: bool = False,
        **kwargs,
    ):
        """
        Send reaction to a message.
    
        Args:
           entity:
           msg_id:
           big:
           reaction:
        """
        result = await self(
            functions.messages.SendReactionRequest(
                peer=entity,
                msg_id=msg_id,
                big=big,
                reaction=utils.convert_reaction(reaction),
                add_to_recent=add_to_recent,
                **kwargs,
            ),
        )
        for update in result.updates:
            if isinstance(update, types.UpdateMessageReactions):
                return update.reactions
            if isinstance(update, types.UpdateEditMessage):
                return update.message.reactions
    
    async def set_quick_reaction(
        self: "TelegramClient",
        reaction: "hints.Reaction",
    ):
        return await functions.messages.SetDefaultReactionRequest(
            reaction=utils.convert_reaction(reaction),
        )

    async def report_reaction(
        self: "TelegramClient",
        peer: "hints.EntityLike",
        id: int,
        reaction_peer: "hints.EntityLike",
    ) -> bool:
        return await self(functions.messages.ReportReactionRequest(peer, id, reaction_peer))
