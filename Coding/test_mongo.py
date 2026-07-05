from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017")
db = client["protein_db"]
print("Databases:", client.list_database_names())
print("Connected successfully!")