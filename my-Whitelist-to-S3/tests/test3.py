import time
import datetime

def my_function():
    now = datetime.datetime.now()
    print("This function is executed every 15 seconds. ",now)

def schedule_my_function():
    while True:
        my_function()
        time.sleep(1)

def main():
    schedule_my_function()