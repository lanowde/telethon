from .. import types, alltlobjects, functions
from ..custom.message import Message as _Message
from ..custom.user import User as USER

class MessageEmpty(_Message, types.MessageEmpty):
    pass


types.MessageEmpty = MessageEmpty
alltlobjects.tlobjects[MessageEmpty.CONSTRUCTOR_ID] = MessageEmpty


class MessageService(_Message, types.MessageService):
    pass


types.MessageService = MessageService
alltlobjects.tlobjects[MessageService.CONSTRUCTOR_ID] = MessageService


class Message(_Message, types.Message):
    pass

class User(USER, types.User):
    pass

types.Message = Message
alltlobjects.tlobjects[Message.CONSTRUCTOR_ID] = Message

types.User = User
alltlobjects.tlobjects[User.CONSTRUCTOR_ID] = User