from pymongo import MongoClient
from bson.objectid import ObjectId

# Replace with your actual MongoDB connection string.
client=MongoClient("mongodb://localhost:27017")
db=client["face_dict"]
credentials_collection=db["auth"]

def insert_credential(username, password):
    credential_data={
        "username":username,
        "password":password,  # In production, store a hashed password.
        "session_token":""    # Initially empty.
    }
    result=credentials_collection.insert_one(credential_data)
    print(f"Inserted credential with _id:{result.inserted_id}")

if __name__=="__main__":
    # Replace these with the desired username and password.
    username=input("Enter username:")
    password=input("Enter password:")
    insert_credential(username, password)
