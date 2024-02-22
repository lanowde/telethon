import typing

from ..tl import types, functions
from .. import utils, hints


if typing.TYPE_CHECKING:
    from .telegramclient import TelegramClient


class TopicMethods:
    async def create_topic(
        self: "TelegramClient",
        entity: "hints.EntityLike",
        title: str,
        icon_color: int = None,
        icon_emoji_id: int = None,
        random_id: int = None,
        send_as: "hints.EntityLike" = None,
    ) -> types.Message:
        """
        Creates a forum topic in the given channel.
        This method is only available in channels, not in supergroups.
    
        Arguments
            entity (`entity`):
                The channel where the forum topic should be created.
    
            title (`str`):
                The title of the forum topic.
    
            icon_color (`int`, optional):
                The color of the icon.
    
            icon_emoji_id (`int`, optional):
                The ID of the emoji.
    
            send_as (`entity`, optional):
                The user who should send the message.
    
        Returns
            The resulting :tl:`Message` object.
    
        Example
            .. code-block:: python
                # Create a forum topic in the channel
                await client.create_forum_topic(
                    channel,
                    'Awesome topic',
                    icon_emoji_id=5454182070156794055,
                )
        """
        entity = await self.get_input_entity(entity)
        if send_as is not None:
            send_as = await self.get_input_entity(send_as)
        return await self(
            functions.channels.CreateForumTopicRequest(
                channel=entity,
                title=title,
                icon_color=icon_color,
                icon_emoji_id=icon_emoji_id,
                random_id=random_id,
                send_as=send_as,
            )
        )

    async def edit_topic(
        self: "TelegramClient",
        entity: "hints.EntityLike",
        topic_id: int,
        title: str = "",
        icon_emoji_id: int = 0,
        closed: bool = False,
    ):
        """
        Edits the given forum topic.
        This method is only available in channels, not in supergroups.
    
        Arguments
            entity (`entity`):
                The channel where the forum topic should be edited.
    
            topic_id (`int`):
                The ID of the topic to edit.
    
            title (`str`, optional):
                The new title of the topic.
    
            icon_emoji_id (`int`, optional):
                The new emoji ID of the topic.
    
            closed (`bool`, optional):
                Whether the topic should be closed or not.
    
        Returns
            The resulting :tl:`Updates` object.
    
        Example
            .. code-block:: python
                # Edit the forum topic in the channel
                await client.edit_forum_topic(
                    channel,
                    123,
                    title='Awesome topic',
                    icon_emoji_id=5454182070156794055,
                )
        """
        entity = await self.get_input_entity(entity)
        return await self(
            functions.channels.EditForumTopicRequest(
                channel=entity,
                topic_id=topic_id,
                title=title,
                icon_emoji_id=icon_emoji_id,
                closed=closed,
            )
        )

    async def get_topics(
        self: "TelegramClient",
        entity: "hints.EntityLike",
        topic_id: typing.List[int] = None,
        offset_date: typing.Optional[datetime.datetime] = None,
        offset_id: int = 0,
        offset_topic: int = 0,
        limit: int = 50,
        query: typing.Optional[str] = None,
    ):
        """
        Gets the forum topics in the given channel.
        This method is only available in channels, not in supergroups.
    
        Arguments
            entity (`entity`):
                The channel where the forum topics should be retrieved.
    
            topic_id (`int`, optional):
                specific topic_id to get.
    
            query (`str`, optional):
                The query to search for.
    
            offset_date (`int`, optional):
                The offset date.
    
            offset_id (`int`, optional):
                The offset ID.
    
            offset_topic (`int`, optional):
                The offset topic.
    
            limit (`int`, optional):
                The maximum number of topics to retrieve.
    
        Returns
            The resulting :tl:`ForumTopics` object.
    
        Example
            .. code-block:: python
                # Get the forum topics in the channel
                await client.get_forum_topics(channel)
        """
        entity = await self.get_input_entity(entity)
        if topic_id is None:
            return await self(
                functions.channels.GetForumTopicsRequest(
                    channel=entity,
                    offset_date=offset_date,
                    offset_id=offset_id,
                    offset_topic=offset_topic,
                    limit=limit,
                    q=query,
                )
            )
        return await self(
            functions.channels.GetForumTopicsByIDRequest(channel=channel, topics=topic_id)
        )
    
    async def update_pinned_topic(
        self: "TelegramClient",
        entity: "hints.EntityLike",
        topic_id: int,
        pinned: bool,
    ) -> types.Updates:
        """
        Pins or unpins the given forum topic.
        This method is only available in channels, not in supergroups.
    
        Arguments
            entity (`entity`):
                The channel where the forum topic should be pinned.
    
            topic_id (`int`):
                The ID of the topic to pin.
    
            pinned (`bool`):
                Whether the topic should be pinned or not.
    
        Returns
            The resulting :tl:`Updates` object.
    
        Example
            .. code-block:: python
                # Pin the forum topic in the channel
                await client.update_pinned_forum_topic(
                    channel,
                    123,
                    True,
                )
        """
        entity = await self.get_input_entity(entity)
        return await self(
            functions.channels.UpdatePinnedForumTopicRequest(
                channel=entity,
                topic_id=topic_id,
                pinned=pinned,
            )
        )
    
    
    async def delete_topic(
        self: "TelegramClient",
        entity: "hints.EntityLike",
        topic_id: int,
    ) -> types.messages.AffectedHistory:
        """
        Deletes the history of the given forum topic.
        This method is only available in channels, not in supergroups.
    
        Arguments
            entity (`entity`):
                The channel where the forum topic should be deleted.
    
            topic_id (`int`):
                The ID of the topic to delete.
    
        Returns
            The resulting :tl:`AffectedHistory` object.
    
        Example
            .. code-block:: python
                # Delete the forum topic in the channel
                await client.delete_topic_history(
                    channel,
                    123,
                )
        """
        entity = await self.get_input_entity(entity)
        return await self(
            functions.channels.DeleteTopicHistoryRequest(
                channel=entity,
                top_msg_id=topic_id,
            )
        )
