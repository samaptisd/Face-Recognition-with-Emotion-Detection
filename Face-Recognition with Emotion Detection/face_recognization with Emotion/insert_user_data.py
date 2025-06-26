from pymongo import MongoClient

# client=MongoClient("mongodb://localhost:27017")
client=MongoClient("mongodb://localhost:27017")
db=client["face_dict"]
users_collection=db["users"]

# user_data={
#     "name": "Shashwati Dora",
#     "emp_id": "",
#     "image_paths": [
#         "/var/www/abm_assistant/user_images/dora_maam.png",
#     ],
# }

user_data=[
        {
                'name': 'Samapti Dikshit',
                'emp_id': 'Samapti Dikshit',
                'image_paths': [
                    r'D:\Samapti\Projects\face_recognization_system\user_images\sampapti_maam.png',
                ],
            },

]

# users_collection.insert_one(user_data)
users_collection.insert_many(user_data)
