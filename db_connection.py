from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import asyncio
import os
import datetime

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME")

if not MONGODB_URI or not MONGODB_DB_NAME:
    raise ValueError("Required MongoDB configuration is missing in the .env file")

class Database:
    def __init__(self, uri: str, db_name: str):
        self.client: AsyncIOMotorClient = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]

    async def list_collection_names(self):
        """ List all collection names in the current database """
        try:
            collections = await self.db.list_collection_names()
            return collections
        except Exception as e:
            print(f"Error listing collections: {e}")
            return []

    async def insert_one(self, collection_name: str, document: dict):
        """ Insert a single document into the specified collection """
        try:
            collection = self.db[collection_name]
            result = await collection.insert_one(document)
            return {"_id": str(result.inserted_id)}  # return inserted id
        except Exception as e:
            print(f"Error inserting document: {e}")
            return {}

    async def find_one(self, collection_name: str, query: dict):
        """ Find a single document in a collection by query """
        try:
            collection = self.db[collection_name]
            document = await collection.find_one(query)
            return document if document else {}
        except Exception as e:
            print(f"Error finding document: {e}")
            return {}

    async def update_one(self, collection_name: str, query: dict, update_data: dict):
        """ Update a single document in the collection """
        try:
            collection = self.db[collection_name]
            result = await collection.update_one(query, {"$set": update_data})
            return {"modified_count": result.modified_count}
        except Exception as e:
            print(f"Error updating document: {e}")
            return {}

    async def delete_one(self, collection_name: str, query: dict):
        """ Delete a single document from the collection """
        try:
            collection = self.db[collection_name]
            result = await collection.delete_one(query)
            return {"deleted_count": result.deleted_count}
        except Exception as e:
            print(f"Error deleting document: {e}")
            return {}

    async def close(self):
        """ Close the connection to the MongoDB server """
        self.client.close()

    async def print_collections(self):
        """ Prints all collection names in the database """
        collections = await self.list_collection_names()
        if collections:
            print("Collections in the database:")
            for collection in collections:
                print(collection)
        else:
            print("No collections found.")

# Create a global database instance for use in other modules
db = Database(MONGODB_URI, MONGODB_DB_NAME)

async def test_insert():
    document = {"name": "Test Document", "created_at": datetime.datetime.now()}
    result = await db.insert_one("TestCollection", document)
    print("Insert result:", result)

async def main():
    await test_insert()  # Insert a document into a collection
    await db.print_collections()  # Check collections again
    await db.close()  # Don't forget to close the connection after operations are done

# Run the asynchronous main function
asyncio.run(main())
