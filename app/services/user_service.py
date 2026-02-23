from app.models.user_model import users_collection

def get_or_create_user(decoded_token):
    uid = decoded_token["uid"]

    user = users_collection.find_one({"firebaseUid": uid})
    
    if not user:
        user = {
            "firebaseUid": uid,
            "name": decoded_token.get("name"),
            "email": decoded_token.get("email"),
            "photoURL": decoded_token.get("picture"),
            "phone": None,
            "location": None,
            "paymentMethods": []
        }
        users_collection.insert_one(user)

    return user