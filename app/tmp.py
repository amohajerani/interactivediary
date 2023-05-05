from threading import Thread
import time


def foo():
    time.sleep(1)
    print('foo completed')


thread = Thread(target=foo)
thread.start()
print('main code finished')
