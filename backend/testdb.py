import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv(".env", override=True)


async def main():
    try:
        connection = await asyncpg.connect(
            user=os.getenv("user"),
            password=os.getenv("password"),
            host=os.getenv("host"),
            port=int(os.getenv("port", "5432")),
            database=os.getenv("dbname", "postgres"),
            ssl="require",
            timeout=15,
        )
        print("SUCCESS: Connected to Supabase!")
        print(await connection.fetchval("SELECT version()"))
        await connection.close()

    except Exception as error:
        print(f"Connection failed: {type(error).__name__}")


asyncio.run(main())