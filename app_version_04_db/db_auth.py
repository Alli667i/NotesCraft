import os
from pymongo import MongoClient
import hashlib
import secrets
from datetime import datetime


class MongoUserAuth:
    def __init__(self):
        # Get MongoDB connection string from environment variable
        mongo_uri = os.getenv("MONGODB_URI")
        if not mongo_uri:
            raise Exception("MONGODB_URI not set in environment variables")

        self.client = MongoClient(mongo_uri)
        self.db = self.client['notescraft']
        self.users = self.db['users']

        # Create index on email for faster lookups
        self.users.create_index("email", unique=True)

    def _hash_password(self, password: str) -> str:
        """Create a secure hash of the password"""
        salt = secrets.token_hex(16)
        password_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        hash_obj = hashlib.sha256(salt_bytes + password_bytes)
        password_hash = hash_obj.hexdigest()
        return f"{salt}:{password_hash}"

    def verify_user(self, email: str, password: str) -> bool:
        """Verify if email and password combination is valid"""
        user = self.users.find_one({"email": email})
        if not user:
            return False

        stored_hash = user.get('password_hash')
        if not stored_hash:
            return False

        try:
            stored_salt, stored_hash_value = stored_hash.split(':', 1)
            password_bytes = password.encode('utf-8')
            salt_bytes = stored_salt.encode('utf-8')
            hash_obj = hashlib.sha256(salt_bytes + password_bytes)
            password_hash = hash_obj.hexdigest()
            return password_hash == stored_hash_value
        except (ValueError, AttributeError):
            return False

    def add_user(self, email: str, password: str, name: str = None) -> bool:
        """Add a new user"""
        try:
            password_hash = self._hash_password(password)

            user_doc = {
                'email': email,
                'name': name or email.split('@')[0],
                'password_hash': password_hash,
                'created_at': datetime.now().isoformat(),
                'active': True
            }

            self.users.insert_one(user_doc)
            print(f"User {email} added successfully")
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False

    def remove_user(self, email: str) -> bool:
        """Remove a user"""
        try:
            result = self.users.delete_one({"email": email})
            if result.deleted_count > 0:
                print(f"User {email} removed")
                return True
            else:
                print(f"User {email} not found")
                return False
        except Exception as e:
            print(f"Error removing user: {e}")
            return False

    def list_users(self):
        """List all users"""
        try:
            users_list = []
            for user in self.users.find({}):
                users_list.append({
                    'email': user.get('email'),
                    'name': user.get('name', ''),
                    'created_at': user.get('created_at', ''),
                    'active': user.get('active', True)
                })
            return users_list
        except Exception as e:
            print(f"Error listing users: {e}")
            return []

    def deactivate_user(self, email: str) -> bool:
        """Deactivate a user"""
        try:
            result = self.users.update_one(
                {"email": email},
                {"$set": {"active": False}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error deactivating user: {e}")
            return False

    def activate_user(self, email: str) -> bool:
        """Activate a user"""
        try:
            result = self.users.update_one(
                {"email": email},
                {"$set": {"active": True}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error activating user: {e}")
            return False

    def is_user_active(self, email: str) -> bool:
        """Check if user is active"""
        user = self.users.find_one({"email": email})
        if user:
            return user.get('active', True)
        return False