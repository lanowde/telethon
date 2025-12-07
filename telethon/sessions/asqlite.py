"""
Async SQLite Session!
"""

import datetime
import os
import time

from ..tl import types, TLObject
from .abstract import Session
from .memory import _SentFileType
from .. import utils
from ..crypto import AuthKey
from ..tl.types import (
    PeerUser,
    PeerChat,
    PeerChannel,
    InputPeerUser,
    InputPeerChat,
    InputPeerChannel,
    InputPhoto,
    InputDocument,
    PeerUser,
    PeerChat,
    PeerChannel,
)

try:
    import aiosqlite

    sqlite3_err = None
except ImportError as e:
    aiosqlite = None
    sqlite3_err = type(e)


EXTENSION = ".session"
CURRENT_VERSION = 8  # database version


class AsyncSQLite(Session):
    """This session contains the required information to login into your
    Telegram account. NEVER give the saved session file to anyone, since
    they would gain instant access to all your messages and contacts.

    If you think the session has been compromised, close all the sessions
    through an official Telegram client to revoke the authorization.
    """

    __slots__ = (
        "_dc_id",
        "_server_address",
        "_port",
        "_auth_key",
        "_tmp_auth_key",
        "_takeout_id",
        "_files",
        "_entities",
        "_update_states",
        "conn",
        "filename",
        "save_entities",
        "store_tmp_auth_key_on_disk",
    )

    def __init__(self, filename=None, store_tmp_auth_key_on_disk: bool = False):
        if aiosqlite is None:
            raise sqlite3_err

        super().__init__()

        self._dc_id = 0
        self._server_address = None
        self._port = None
        self._auth_key = None
        self._tmp_auth_key = None
        self._takeout_id = None

        self._files = {}
        self._entities = set()
        self._update_states = {}

        self.filename = filename
        self.save_entities = True
        self.store_tmp_auth_key_on_disk = store_tmp_auth_key_on_disk

        if self.filename:
            if not self.filename.endswith(EXTENSION):
                self.filename += EXTENSION

    async def _initiate(self):
        self.conn = await aiosqlite.connect(self.filename, timeout=10, autocommit=True)
        resp = await self.conn.execute(
            "select name from sqlite_master where type='table' and name='version'"
        )
        if await resp.fetchone():
            # Tables already exist, check for the version
            resp = await self.conn.execute("select version from version")
            version = (await resp.fetchone())[0]
            if version < CURRENT_VERSION:
                await self._upgrade_database(old=version)
                await self.conn.execute("delete from version")
                await self.conn.execute(
                    "insert into version values (?)", (CURRENT_VERSION,)
                )
                await self.save()

            # These values will be saved
            tuple_ = await self._execute("select * from sessions")
            if tuple_:
                (
                    self._dc_id,
                    self._server_address,
                    self._port,
                    key,
                    tmp_key,
                    self._takeout_id,
                ) = tuple_
                self._auth_key = AuthKey(data=key)
                self._tmp_auth_key = AuthKey(data=tmp_key)
        else:
            # Tables don't exist, create new ones
            await self._create_table(
                "version (version integer primary key)",
                """sessions (
                    dc_id integer primary key,
                    server_address text,
                    port integer,
                    auth_key blob,
                    takeout_id integer,
                    tmp_auth_key blob
                )""",
                """entities (
                    id integer primary key,
                    hash integer not null,
                    username text,
                    phone integer,
                    name text,
                    date integer
                )""",
                """sent_files (
                    md5_digest blob,
                    file_size integer,
                    type integer,
                    id integer,
                    hash integer,
                    primary key(md5_digest, file_size, type)
                )""",
                """update_state (
                    id integer primary key,
                    pts integer,
                    qts integer,
                    date integer,
                    seq integer
                )""",
            )
            await self.conn.execute(
                "insert into version values (?)", (CURRENT_VERSION,)
            )
            await self._update_session_table()

    async def clone(self, to_instance=None):
        raise NotImplementedError

    async def _upgrade_database(self, old):
        if old == 1:
            old += 1
            # old == 1 doesn't have the old sent_files so no need to drop
        if old == 2:
            old += 1
            # Old cache from old sent_files lasts then a day anyway, drop
            await self.conn.execute("drop table sent_files")
            await self._create_table(
                """sent_files (
                md5_digest blob,
                file_size integer,
                type integer,
                id integer,
                hash integer,
                primary key(md5_digest, file_size, type)
            )""",
            )
        if old == 3:
            old += 1
            await self._create_table(
                """update_state (
                id integer primary key,
                pts integer,
                qts integer,
                date integer,
                seq integer
            )""",
            )
        if old == 4:
            old += 1
            await self.conn.execute(
                "alter table sessions add column takeout_id integer"
            )
        if old == 5:
            # Not really any schema upgrade, but potentially all access
            # hashes for User and Channel are wrong, so drop them off.
            old += 1
            await self.conn.execute("delete from entities")
        if old == 6:
            old += 1
            await self.conn.execute("alter table entities add column date integer")
        if old == 7:
            old += 1
            await self.conn.execute("alter table sessions add column tmp_auth_key blob")

    async def _create_table(self, *definitions):
        for definition in definitions:
            await self.conn.execute("create table {}".format(definition))

    # Data from sessions should be kept as properties
    # not to fetch the database every time we need it
    async def set_dc(self, dc_id, server_address, port):
        self._dc_id = dc_id or 0
        self._server_address = server_address
        self._port = port
        await self._update_session_table()

        # Fetch the auth_key corresponding to this data center
        row = await self._execute("select auth_key, tmp_auth_key from sessions")
        if row and row[0]:
            self._auth_key = AuthKey(data=row[0])
            await self._update_session_table()
        else:
            self._auth_key = None

        if row and row[1]:
            self._tmp_auth_key = AuthKey(data=row[1])
            await self._update_session_table()
        else:
            self._tmp_auth_key = None

    @property
    def dc_id(self):
        return self._dc_id

    @property
    def server_address(self):
        return self._server_address

    @property
    def port(self):
        return self._port

    @property
    def auth_key(self):
        return self._auth_key

    @property
    def tmp_auth_key(self):
        return self._tmp_auth_key

    @property
    def takeout_id(self):
        return self._takeout_id

    @auth_key.setter
    def auth_key(self, value):
        self._auth_key = value

    @tmp_auth_key.setter
    def tmp_auth_key(self, value):
        self._tmp_auth_key = value

    @takeout_id.setter
    def takeout_id(self, value):
        self._takeout_id = value

    async def _update_session_table(self):
        # While we can save multiple rows into the sessions table
        # currently we only want to keep ONE as the tables don't
        # tell us which auth_key's are usable and will work. Needs
        # some more work before being able to save auth_key's for
        # multiple DCs. Probably done differently.
        await self.conn.execute("delete from sessions")
        await self.conn.execute(
            "insert or replace into sessions values (?,?,?,?,?,?)",
            (
                self._dc_id,
                self._server_address,
                self._port,
                self._auth_key.key if self._auth_key else b"",
                self._takeout_id,
                self._tmp_auth_key.key
                if (self.store_tmp_auth_key_on_disk and self._tmp_auth_key)
                else b"",
            ),
        )

    async def get_update_state(self, entity_id):
        row = await self.conn.execute(
            "select pts, qts, date, seq from update_state where id = ?", entity_id
        )
        if row:
            pts, qts, date, seq = row
            date = datetime.datetime.fromtimestamp(date, tz=datetime.timezone.utc)
            return types.updates.State(pts, qts, date, seq, unread_count=0)

    async def set_update_state(self, entity_id, state):
        await self._execute(
            "insert or replace into update_state values (?,?,?,?,?)",
            entity_id,
            state.pts,
            state.qts,
            state.date.timestamp(),
            state.seq,
        )

    async def get_update_states(self):
        resp = await self.conn.execute(
            "select id, pts, qts, date, seq from update_state"
        )
        rows = await resp.fetchall()
        return (
            (
                row[0],
                types.updates.State(
                    pts=row[1],
                    qts=row[2],
                    date=datetime.datetime.fromtimestamp(
                        row[3], tz=datetime.timezone.utc
                    ),
                    seq=row[4],
                    unread_count=0,
                ),
            )
            for row in rows
        )

    async def _execute(self, stmt, *values):
        """
        Gets a cursor, executes `stmt` and closes the cursor,
        fetching one row afterwards and returning its result.
        """
        resp = await self.conn.execute(stmt, values)
        return await resp.fetchone()

    async def save(self):
        """Saves the current session object as session_user_id.session"""
        # This is a no-op if there are no changes to commit, so there's
        # no need for us to keep track of an "unsaved changes" variable.
        await self.conn.commit()

    async def close(self):
        """Closes the connection unless we're working in-memory"""
        if self.filename != ":memory:":
            await self.conn.commit()
            await self.conn.close()
            self.conn = None

    async def delete(self):
        raise NotImplementedError

    @classmethod
    def list_sessions(cls):
        """Lists all the sessions of the users who have ever connected
        using this client and never logged out
        """
        return [
            os.path.splitext(os.path.basename(f))[0]
            for f in os.listdir(".")
            if f.endswith(EXTENSION)
        ]

    # Entity processing

    async def process_entities(self, tlo):
        """
        Processes all the found entities on the given TLObject,
        unless .save_entities is False.
        """
        if not self.save_entities:
            return

        rows = self._entities_to_rows(tlo)
        if not rows:
            return

        now_tup = (int(time.time()),)
        rows = [row + now_tup for row in rows]
        await self.conn.executemany(
            "insert or replace into entities values (?,?,?,?,?,?)", rows
        )

    async def get_entity_rows_by_phone(self, phone):
        return await self._execute(
            "select id, hash from entities where phone = ?", phone
        )

    async def get_entity_rows_by_username(self, username):
        resp = await self.conn.execute(
            "select id, hash, date from entities where username = ?", (username,)
        )
        results = await resp.fetchall()

        if not results:
            return None

        # If there is more than one result for the same username, evict the oldest one
        if len(results) > 1:
            results.sort(key=lambda t: t[2] or 0)
            await self.conn.executemany(
                "update entities set username = null where id = ?",
                [(t[0],) for t in results[:-1]],
            )

        return results[-1][0], results[-1][1]

    async def get_entity_rows_by_name(self, name):
        return await self._execute("select id, hash from entities where name = ?", name)

    async def get_entity_rows_by_id(self, id, exact=True):
        if exact:
            return await self._execute("select id, hash from entities where id = ?", id)
        else:
            return await self._execute(
                "select id, hash from entities where id in (?,?,?)",
                utils.get_peer_id(PeerUser(id)),
                utils.get_peer_id(PeerChat(id)),
                utils.get_peer_id(PeerChannel(id)),
            )

    async def get_input_entity(self, key):
        try:
            if key.SUBCLASS_OF_ID in (0xC91C90B6, 0xE669BF46, 0x40F202FD):
                # hex(crc32(b'InputPeer', b'InputUser' and b'InputChannel'))
                # We already have an Input version, so nothing else required
                return key
            # Try to early return if this key can be casted as input peer
            return utils.get_input_peer(key)
        except (AttributeError, TypeError):
            # Not a TLObject or can't be cast into InputPeer
            if isinstance(key, TLObject):
                key = utils.get_peer_id(key)
                exact = True
            else:
                exact = not isinstance(key, int) or key < 0

        result = None
        if isinstance(key, str):
            phone = utils.parse_phone(key)
            if phone:
                result = await self.get_entity_rows_by_phone(phone)
            else:
                username, invite = utils.parse_username(key)
                if username and not invite:
                    result = await self.get_entity_rows_by_username(username)
                else:
                    tup = utils.resolve_invite_link(key)[1]
                    if tup:
                        result = await self.get_entity_rows_by_id(tup, exact=False)

        elif isinstance(key, int):
            result = await self.get_entity_rows_by_id(key, exact)

        if not result and isinstance(key, str):
            result = await self.get_entity_rows_by_name(key)

        if result:
            entity_id, entity_hash = result  # unpack resulting tuple
            entity_id, kind = utils.resolve_id(entity_id)
            # removes the mark and returns type of entity
            if kind == PeerUser:
                return InputPeerUser(entity_id, entity_hash)
            elif kind == PeerChat:
                return InputPeerChat(entity_id)
            elif kind == PeerChannel:
                return InputPeerChannel(entity_id, entity_hash)
        else:
            raise ValueError("Could not find input entity with key ", key)

    @staticmethod
    def _entity_values_to_row(id, hash, username, phone, name):
        # While this is a simple implementation it might be overrode by,
        # other classes so they don't need to implement the plural form
        # of the method. Don't remove.
        return id, hash, username, phone, name

    def _entity_to_row(self, e):
        if not isinstance(e, TLObject):
            return
        try:
            p = utils.get_input_peer(e, allow_self=False)
            marked_id = utils.get_peer_id(p)
        except TypeError:
            # Note: `get_input_peer` already checks for non-zero `access_hash`.
            #        See issues #354 and #392. It also checks that the entity
            #        is not `min`, because its `access_hash` cannot be used
            #        anywhere (since layer 102, there are two access hashes).
            return

        if isinstance(p, (InputPeerUser, InputPeerChannel)):
            p_hash = p.access_hash
        elif isinstance(p, InputPeerChat):
            p_hash = 0
        else:
            return

        username = getattr(e, "username", None) or None
        if username is not None:
            username = username.lower()
        phone = getattr(e, "phone", None)
        name = utils.get_display_name(e) or None
        return self._entity_values_to_row(marked_id, p_hash, username, phone, name)

    def _entities_to_rows(self, tlo):
        if not isinstance(tlo, TLObject) and utils.is_list_like(tlo):
            # This may be a list of users already for instance
            entities = tlo
        else:
            entities = []
            if hasattr(tlo, "user"):
                entities.append(tlo.user)
            if hasattr(tlo, "chat"):
                entities.append(tlo.chat)
            if hasattr(tlo, "chats") and utils.is_list_like(tlo.chats):
                entities.extend(tlo.chats)
            if hasattr(tlo, "users") and utils.is_list_like(tlo.users):
                entities.extend(tlo.users)

        rows = []  # Rows to add (id, hash, username, phone, name)
        for e in entities:
            row = self._entity_to_row(e)
            if row:
                rows.append(row)
        return rows

    def process_entities(self, tlo):
        self._entities |= set(self._entities_to_rows(tlo))

    # File processing

    async def get_file(self, md5_digest, file_size, cls):
        row = await self._execute(
            "select id, hash from sent_files "
            "where md5_digest = ? and file_size = ? and type = ?",
            md5_digest,
            file_size,
            _SentFileType.from_type(cls).value,
        )
        if row:
            # Both allowed classes have (id, access_hash) as parameters
            return cls(row[0], row[1])

    async def cache_file(self, md5_digest, file_size, instance):
        if not isinstance(instance, (InputDocument, InputPhoto)):
            raise TypeError("Cannot cache %s instance" % type(instance))

        await self._execute(
            "insert or replace into sent_files values (?,?,?,?,?)",
            md5_digest,
            file_size,
            _SentFileType.from_type(type(instance)).value,
            instance.id,
            instance.access_hash,
        )
