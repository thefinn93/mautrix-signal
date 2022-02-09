# mautrix-signal - A Matrix-Signal puppeting bridge
# Copyright (C) 2022 Tulir Asokan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from mautrix.util.async_db import Connection

from . import upgrade_table


@upgrade_table.register(description="Allow phone numbers as message sender identifiers")
async def upgrade_v4(conn: Connection, scheme: str) -> None:
    if scheme == "sqlite":
        # SQLite doesn't have anything in the tables yet,
        # so just recreate them without migrating data
        await conn.execute("DROP TABLE message")
        await conn.execute("DROP TABLE reaction")
        await conn.execute(
            """
            CREATE TABLE message (
                mxid    TEXT NOT NULL,
                mx_room TEXT NOT NULL,
                sender          TEXT,
                timestamp       BIGINT,
                signal_chat_id  TEXT,
                signal_receiver TEXT,

                PRIMARY KEY (sender, timestamp, signal_chat_id, signal_receiver),
                FOREIGN KEY (signal_chat_id, signal_receiver) REFERENCES portal(chat_id, receiver)
                    ON UPDATE CASCADE ON DELETE CASCADE,
                UNIQUE (mxid, mx_room)
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE reaction (
                mxid    TEXT NOT NULL,
                mx_room TEXT NOT NULL,

                signal_chat_id  TEXT   NOT NULL,
                signal_receiver TEXT   NOT NULL,
                msg_author      TEXT   NOT NULL,
                msg_timestamp   BIGINT NOT NULL,
                author          TEXT   NOT NULL,

                emoji TEXT NOT NULL,

                PRIMARY KEY (signal_chat_id, signal_receiver, msg_author, msg_timestamp, author),
                FOREIGN KEY (msg_author, msg_timestamp, signal_chat_id, signal_receiver)
                    REFERENCES message(sender, timestamp, signal_chat_id, signal_receiver)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                UNIQUE (mxid, mx_room)
            )
            """
        )
        return

    cname = await conn.fetchval(
        "SELECT constraint_name FROM information_schema.table_constraints "
        "WHERE table_name='reaction' AND constraint_name LIKE '%_fkey'"
    )
    await conn.execute(f"ALTER TABLE reaction DROP CONSTRAINT {cname}")
    await conn.execute("ALTER TABLE reaction ALTER COLUMN msg_author SET DATA TYPE TEXT")
    await conn.execute("ALTER TABLE reaction ALTER COLUMN author SET DATA TYPE TEXT")
    await conn.execute("ALTER TABLE message ALTER COLUMN sender SET DATA TYPE TEXT")
    await conn.execute(
        f"ALTER TABLE reaction ADD CONSTRAINT {cname} "
        "FOREIGN KEY (msg_author, msg_timestamp, signal_chat_id, signal_receiver) "
        "  REFERENCES message(sender, timestamp, signal_chat_id, signal_receiver) "
        "  ON DELETE CASCADE ON UPDATE CASCADE"
    )
