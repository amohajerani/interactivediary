import time
import threading
import schedule

from data import get_summary


def run_get_summary():
    job_thread = threading.Thread(target=get_summary)
    job_thread.start()


if __name__ == '__main__':
    schedule.every().hour.do(run_get_summary)
    while True:
        schedule.run_pending()
        time.sleep(60)  # after testing change this to 60 seconds or more
