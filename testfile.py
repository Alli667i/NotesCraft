from pymongo import MongoClient

# Your connection string
mongo_uri = "mongodb+srv://moheetahmad54_db_user:<db_password>@cluster0.7qwcghu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(mongo_uri)
    # Try to ping the database
    client.admin.command('ping')
    print("✅ Connected successfully!")
except Exception as e:
    print(f"❌ Connection failed: {e}")