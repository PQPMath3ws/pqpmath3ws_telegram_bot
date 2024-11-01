from sqlite3 import connect, Connection


class Database:
    con = None

    def __init__(self, db_file: str) -> None:
        self.db_file = db_file

    def __createDatabaseStructure(self) -> None:
        global con
        con.cursor().execute(
            """CREATE TABLE IF NOT EXISTS "users" (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, user_id BIGINT NOT NULL UNIQUE, username TEXT NOT NULL UNIQUE, createdAt DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL);"""
        )
        con.cursor().execute(
            """CREATE TABLE IF NOT EXISTS "users_states" (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, user_id BIGINT NOT NULL, chat_id BIGINT NOT NULL, username TEXT NOT NULL, user_state TEXT DEFAULT "welcome_message" NOT NULL, createdAt DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, FOREIGN KEY(user_id) REFERENCES users(user_id));"""
        )
        con.cursor().execute(
            """CREATE TABLE IF NOT EXISTS "users_proposals" (id TEXT NOT NULL PRIMARY KEY UNIQUE, user_id BIGINT NOT NULL, proposal TEXT NOT NULL, isConfirmed TINYINT, createdAt DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, FOREIGN KEY(user_id) REFERENCES users(user_id));"""
        )
        con.cursor().execute(
            """CREATE TABLE IF NOT EXISTS "users_newsletter" (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, user_id BIGINT NOT NULL, createdAt DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, FOREIGN KEY(user_id) REFERENCES users(user_id));"""
        )
        con.cursor().execute(
            """CREATE TABLE IF NOT EXISTS "users_bloqued_bot" (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, user_id BIGINT NOT NULL, createdAt DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, FOREIGN KEY(user_id) REFERENCES users(user_id));"""
        )

    def initDatabase(self) -> Connection:
        global con
        con = connect(self.db_file)
        self.__createDatabaseStructure()
        return con

    def closeDatabase(self) -> None:
        global con
        con.close()

    def get_users_states(self) -> dict:
        global con
        result = con.cursor().execute("""SELECT * FROM "users_states";""").fetchall()
        states = {}
        if len(result) > 0:
            for user in result:
                states[user[2]] = {
                    "chat_id": user[2],
                    "username": user[3],
                    "user_state": user[4],
                }
        return states

    def check_user_exists(self, user_id: int) -> bool:
        global con
        result = (
            con.cursor()
            .execute(f"""SELECT * FROM "users" WHERE "user_id" = {user_id} LIMIT 1;""")
            .fetchone()
        )
        if result:
            return True
        else:
            return False

    def create_user(self, user_id: int, username: str, chat_id: int) -> None:
        global con
        con.cursor().execute(
            f"""INSERT INTO "users" ("user_id", "username") VALUES ({user_id}, "{username}");"""
        )
        con.cursor().execute(
            f"""INSERT INTO "users_states" ("user_id", "chat_id", "username") VALUES ({user_id}, {chat_id}, "{username}");"""
        )
        con.commit()

    def update_user(
        self, user_id: int, username: str, chat_id: int, user_state: str
    ) -> None:
        global con
        con.cursor().execute(
            f"""UPDATE "users" SET "username" = "{username}", "updatedAt" = CURRENT_TIMESTAMP WHERE "user_id" = {user_id};"""
        )
        result = (
            con.cursor()
            .execute(
                f"""SELECT "id" FROM "users_states" WHERE "user_id" = {user_id} AND "chat_id" = {chat_id} LIMIT 1;"""
            )
            .fetchone()
        )
        if result:
            con.cursor().execute(
                f"""UPDATE "users_states" SET "chat_id" = {chat_id}, "username" = "{username}", "user_state" = "{user_state}", updatedAt = CURRENT_TIMESTAMP WHERE "user_id" = {user_id} AND "chat_id" = {chat_id};"""
            )
        else:
            con.cursor().execute(
                f"""INSERT INTO "users_states" ("user_id", "chat_id", "username", "user_state") VALUES ({user_id}, {chat_id}, "{username}", "{user_state}");"""
            )
        if user_id == chat_id:
            con.cursor().execute(
                f"""DELETE FROM "users_bloqued_bot" WHERE "user_id" = {user_id};"""
            )
        con.commit()

    def insertUserBloquedBot(self, user_id: int) -> None:
        global con
        con.cursor.execute(
            f"""INSERT INTO "users_bloqued_bot" ("user_id") VALUES ({user_id});"""
        )
        con.cursor.execute(
            f"""UPDATE "users_states" SET "user_state" = "user_bloqued_bot" WHERE "user_id" = {user_id} AND "chat_id" = {user_id};"""
        )
        con.cursor().execute(
            f"""DELETE FROM "users_newsletter" WHERE "user_id" = {user_id};"""
        )
        con.commit()

    def createProposal(self, proposal_id: str, user_id: int, proposal: str) -> None:
        global con
        con.cursor().execute(
            f"""INSERT INTO "users_proposals" ("id", "user_id", "proposal") VALUES ("{proposal_id}", {user_id}, "{proposal}");"""
        )
        con.commit()

    def updateStatusOfProposal(self, proposal_id: str, isConfirmed: int) -> None:
        global con
        con.cursor().execute(
            f"""UPDATE "users_proposals" SET "isConfirmed" = {isConfirmed}, updatedAt = CURRENT_TIMESTAMP WHERE "id" = "{proposal_id}";"""
        )
        con.commit()

    def getProposal(self, proposal_id: str) -> dict | None:
        global con
        proposal_result = (
            con.cursor()
            .execute(
                f"""SELECT "user_id", "proposal" FROM "users_proposals" WHERE "id" = "{proposal_id}" LIMIT 1;"""
            )
            .fetchone()
        )
        if proposal_result:
            user_result = (
                con.cursor()
                .execute(
                    f"""SELECT "username" FROM "users" WHERE "user_id" = "{proposal_result[0]}";"""
                )
                .fetchone()
            )
            if user_result:
                proposal: dict = {
                    "proposal": proposal_result[1],
                    "user": user_result[0],
                }
                return proposal
            else:
                return None
        else:
            return None

    def check_can_newsletter_user(self, user_id: int) -> bool:
        global con
        result = (
            con.cursor()
            .execute(
                f"""SELECT * FROM "users_newsletter" WHERE "user_id" = {user_id} LIMIT 1;"""
            )
            .fetchone()
        )
        if result:
            return True
        else:
            return False

    def register_user_to_newsletter(self, user_id: int) -> None:
        global con
        con.cursor().execute(
            f"""INSERT INTO "users_newsletter" ("user_id") VALUES ({user_id});"""
        )
        con.commit()

    def unregister_user_to_newsletter(self, user_id: int) -> None:
        global con
        con.cursor().execute(
            f"""DELETE FROM "users_newsletter" WHERE "user_id" = {user_id};"""
        )
        con.commit()

    def getAllSubscribers(self):
        global con
        result = (
            con.cursor()
            .execute(
                """SELECT "users_states"."username" FROM "users_states" INNER JOIN "users_newsletter" ON "users_newsletter"."user_id" = "users_states"."user_id";"""
            )
            .fetchall()
        )
        if len(result) > 0:
            return result
        else:
            return None
