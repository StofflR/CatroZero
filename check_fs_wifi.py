import sys
import os
import datetime
import time
import logging
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import filecmp

USB_PATH = "/mnt/piusb"
WIFI_PATH = os.getcwd()+"/wifi"
DATA_LOCATION = "/piusb.bin"
MOUNT = "sudo mount "+DATA_LOCATION+" "+USB_PATH
UNMOUNT = "sudo umount "+USB_PATH
ENABLE_OTG = "sudo modprobe g_mass_storage file="+DATA_LOCATION+" stall=0 removable=1" 
DISABLE_OTG = "sudo modprobe -r g_mass_storage"

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%s")
    path = sys.argv[1] if len(sys.argv) > 1 else WIFI_PATH
    
    print("PATH:" + path)
    event_handler = Handler(path)
    event_handler.replug()
    print("Starting Watching")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        event_handler.stop()
    event_handler.join()
    print("Stopped Watching")

class Handler(FileSystemEventHandler):
    def __init__(self, path):
        self.path = path
        self.observer = Observer()
        self.observer.schedule(self, path=path, recursive=True)
        self.observer.start()
        self.terminating = threading.Lock()
        self.timeout_start = None       
        self.timeout_lock = threading.Lock()
    
    def stop(self):
        self.observer.stop()

    def join(self):
        self.observer.join()

    def terminate(self):
        self.terminating.acquire()
        print("Stopped Watching")
        os.execl(sys.executable, sys.executable, *sys.argv)
        #for Windows
        self.terminating.release()
        exit(0)

    def replug(self, soft=False):
        os.system("sudo rm -rf " + USB_PATH+"/*")
        os.system("sudo cp -r -u " + WIFI_PATH + "/. " + USB_PATH)
        os.system(DISABLE_OTG)
        #if os.system("sudo service smbd restart"):
        #  raise RuntimeError("Error")
       # os.system(DISABLE_OTG)
        os.system(UNMOUNT)
        #os.system("sudo service smbd start")
        os.system(MOUNT)
        os.system(ENABLE_OTG)
        #os.system("sudo service smbd start")
        pass

    def sameFiles(self, path_a, path_b):
        comp = filecmp.dircmp(a=path_a, b=path_b)
        return (comp.left_only == [] and comp.right_only == [])

    def init_timeout(self):
        self.timeout_lock.acquire()
        self.timeout_start = datetime.datetime.now()

    def timeout(self, time):
        return abs(self.timeout_start.timedelta(datetime.datetime.now()).seconds) > 2 

    def on_any_event(self, event):
        if event.event_type == 'closed' or event.event_type == 'moved' or event.event_type == 'deleted' or event.event_type == "modified":
            self.init_timeout()
            while(self.sameFiles(self.path, USB_PATH)):
                if self.timeout(2): 
                    self.timeout_lock.release()
                    return
        # Event is modified, you can process it now
            print("Watchdog received modified event - % s." % event.src_path)
            self.observer.stop()
            self.terminate()
        print(event.event_type)
 
if __name__ == '__main__':
    main()
    
    

