import time
import os
import random

LOG_FILE = "/shared/terraform.log"

FAILURES = [
    "Error: Resource 'aws_instance.web' already exists",
    "Error: Failed to connect to AWS API",
    "Error: Invalid credentials",
    "Error: Resource 'aws_db_instance.default' failed to create: Storage quota exceeded"
]

def generate_log():
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    failure = random.choice(FAILURES)
    log_entry = f"[{timestamp}] {failure}\n"
    
    with open(LOG_FILE, "a") as f:
        f.write(log_entry)
    print(f"Generated failure: {failure}")

if __name__ == "__main__":
    # Ensure the directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    while True:
        generate_log()
        time.sleep(120)  # 2 minutes
