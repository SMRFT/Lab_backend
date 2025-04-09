import os
import datetime
password= 'Smrft@2024'
# MongoDB Atlas URI
atlas_uri = "mongodb+srv://shinovalab:<db_password>@cluster0.xbq9c.mongodb.net/Lab"

# Local MongoDB URI
local_uri = "mongodb://127.0.0.1:27017/LabBackup"

# Backup folder
backup_folder = "mongo_backup"
os.makedirs(backup_folder, exist_ok=True)

# Timestamp for backup
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = os.path.join(backup_folder, f"backup_{timestamp}")

# Step 1: Dump data from MongoDB Atlas
os.system(f"mongodump --uri={atlas_uri} --out={backup_path}")

# Step 2: Restore data to Local MongoDB
os.system(f"mongorestore --uri={local_uri} {backup_path}")

print(f"Backup completed: {backup_path}")
