import firebase_admin
from firebase_admin import credentials, firestore
import json
# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Create data
# user_data = {
#     "username": "Jay",
#     "json": {
#         "age": 23,
#         "city": "Indore",
#         "languages": ["Python", "Java"]
#     }
# }
user_data = {}
# read JSON file
with open("sample.json", "r") as file:
    file_data = json.load(file)
    user_data["username"] = file_data["username"]
    user_data["json"] = file_data["json"]
print("Data to be saved:", user_data)

# Save
db.collection("DDNA").document(user_data["username"]).set(user_data)
print("Data saved!")

# Read
doc = db.collection("DDNA").document(f"{user_data['username']}").get()
if doc.exists:
    print("Retrieved:", doc.to_dict())
