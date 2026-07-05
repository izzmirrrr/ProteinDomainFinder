# database.py
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from config import settings

client = MongoClient(settings.MONGODB_URL)
db = client[settings.DATABASE_NAME]

proteins_collection = db["proteins"]
users_collection = db["users"]
history_collection = db["predictions"]
popular_collection = db["popular_searches"]
password_resets_collection = db["password_resets"]

def init_indexes():
    """Create indexes used by the API. Safe to call repeatedly."""
    try:
        for idx_name, idx in users_collection.index_information().items():
            if idx_name == "_id_":
                continue
            key = idx.get("key")
            if key == [("username", 1)]:
                users_collection.drop_index(idx_name)
            elif key in ([("email", 1)], [("user_id", 1)]) and not idx.get("unique"):
                users_collection.drop_index(idx_name)
    except Exception:
        pass

    try:
        for idx_name, idx in password_resets_collection.index_information().items():
            if idx_name == "_id_":
                continue
            if idx.get("key") == [("token_hash", 1)]:
                password_resets_collection.drop_index(idx_name)
    except Exception:
        pass

    proteins_collection.create_index([("protein_id", ASCENDING)], unique=True)
    proteins_collection.create_index([("sequence", ASCENDING)])
    proteins_collection.create_index(
        [("protein_id", TEXT), ("protein_name", TEXT), ("organism", TEXT), ("header", TEXT)],
        name="protein_text_search",
        default_language="english",
    )
    users_collection.create_index([("user_id", ASCENDING)], unique=True)
    users_collection.create_index([("email", ASCENDING)], unique=True)
    history_collection.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
    history_collection.create_index([("query_hash", ASCENDING)])
    popular_collection.create_index([("query_hash", ASCENDING)], unique=True)
    popular_collection.create_index([("count", DESCENDING)])
    password_resets_collection.create_index([("user_id", ASCENDING), ("code_hash", ASCENDING)])
    password_resets_collection.create_index([("user_id", ASCENDING), ("expires_at", ASCENDING)])
    password_resets_collection.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)

init_indexes()

def get_db():
    return proteins_collection

def get_users_collection():
    return users_collection

def get_history_collection():
    return history_collection

def get_popular_collection():
    return popular_collection

def get_password_resets_collection():
    return password_resets_collection
