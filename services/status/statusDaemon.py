import subprocess
import psycopg2
from time import sleep
import signal
import sys

# Define a flag to track whether a signal has been received
signal_received = False

# Define a signal handler function to handle SIGTERM and SIGINT signals
def signal_handler(signum, frame):
    global signal_received
    print("Received a termination signal. Cleaning up...")
    # Perform any necessary cleanup here
    signal_received = True

# Register the signal handler for SIGTERM and SIGINT
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def connect():
    db_config = {
        'dbname': 'polarDB',
        'user': 'polarPL',
        'password': 'polarpswd',
        'host': 'db',
        'port': '5432',
    }
    return psycopg2.connect(**db_config)

while not signal_received:
    try:

        # queue = subprocess.run(['celery', '-A', 'tasks', 'queue'])

        completed_process = subprocess.run(['celery', '-A', 'tasks', 'status'], text=True, capture_output=True)
        status = completed_process.stdout.replace('->', '').replace('celery@', '').replace(' ', '').split('\n')
        statusList = {}
        for node in status:
            if ':' in node:
                statusList[node.split(':')[0]] = node.split(':')[1]

        conn = connect()
        cursor = conn.cursor()

        for name, status in statusList.items():
            # Update or insert row
            cursor.execute("""
            INSERT INTO status (name, status)
            VALUES (%s, %s)
            ON CONFLICT (name) DO UPDATE
            SET status = EXCLUDED.status
            """, (name, status))

        # Set offline for any names not in statusList
        if statusList:
            cursor.execute("""
                DELETE FROM status
                WHERE name NOT IN %s
            """, (tuple(statusList.keys()),))

        if not statusList:
            cursor.execute("""
                UPDATE status 
                SET status = 'OFFLINE'
            """)

        conn.commit()
        conn.close()
    except Exception as e:
        print(e)
    sleep(10)

# Perform any final cleanup actions here
print("Cleaning up before exit...")
sys.exit(0)
