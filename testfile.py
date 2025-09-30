from datetime import datetime


now = datetime.now()
current_time = now.strftime("%I:%M:%S")

print(current_time)