######################################################
#                   DuckHunter                       #
#                 Pedro M. Sosa                      #
# Tool to prevent getting attacked by a rubberducky! #
######################################################

from ctypes import *
import pythoncom
import pyWinhook 
import win32clipboard
import win32ui
import os
import shutil
from time import gmtime, strftime
from sys import stdout
import imp
import statistics
duckhunt = imp.load_source('duckhunt', 'F:/Tugas Kuliah/Semester 8/duckhunt-upgraded/duckhunt-upgraded/duckhunt.conf')

##### NOTES #####
#
# 1. Undestanding Protection Policy:
#   - Paranoid: When an  attack is detected, lock down any further keypresses until the correct password is entered. (set password in .conf file). Attack will also be logged.
#   - Normal :  When an attack is detected, keyboard input will temporarily be disallowed. (After it is deemed that the treat is over, keyboard input will be allowed again). Attack will also be logged.
#   - Sneaky: When an attacks is detected, a few keys will be dropped (enough to break any attack, make it look as if the attacker messed up.) Attack will also be logged.
#   - LogOnly: When an attack is detected, simply log the attack and in no way stop it. 

# 2. How To Use
#   - Modify the user configurable vars below. (particularly policy and password)
#   - Turn the program into a .pyw to run it as windowless script.
#   - (Opt) Use py2exe to build an .exe
#
#################




keystroke_threshold = duckhunt.keythreshold # Consistency Threshold
threshold  = duckhunt.threshold      # Speed Threshold
size       = duckhunt.size           # Size of history array
policy     = duckhunt.policy.lower() # Designate Policy Type
password   = duckhunt.password       # Password used in Paranoid Mode
allow_auto_type_software = duckhunt.allow_auto_type_software #Allow AutoType Software (eg. KeyPass or LastPass)
################################################################################
pcounter   = 0                       # Password Counter (If using password)
speed      = 0                       # Current Average Keystroke Speed
prevTime   = -1                      # Previous Keypress Timestamp
i          = 0                       # History Array Timeslot
intrusion  = False                   # Boolean Flag to be raised in case of intrusion detection
history    = [threshold+1] * size    # Array for keeping track of average speeds across the last n keypresses
randdrop   = duckhunt.randdrop       # How often should one drop a letter (in Sneaky mode)
prevWindow = []                      # What was the previous window
filename   = duckhunt.filename       # Filename to save attacks
blacklist  = duckhunt.blacklist       # Program Blacklist


#Logging the Attack
def log(event):
    global prevWindow

    with open(filename, "a+", encoding='utf-8') as x:
        if (prevWindow != event.WindowName):
            x.write("\n[ %s ]\n" % (event.WindowName))
            prevWindow = event.WindowName
        if event.Ascii > 32 and event.Ascii < 127:
            x.write("[%c]" % event.Ascii)
            x.write("\t Speed[%f]\t" % speed)
            x.write("Consistency[%f]\n" % keystroke_std)
        else:
            x.write("[%s]\t" % event.Key)
            x.write("Speed[%f]\t" % speed)
            x.write("Consistency[%f]\n" % keystroke_std)

    return


def caught(event):
    global intrusion, policy, randdrop
    print ("Quack! Quack! -- Time to go Duckhunting!")
    intrusion = True;

    #Paranoid Policy
    if (policy == "paranoid"):
        win32ui.MessageBox("Someone might be trying to inject keystrokes into your computer.\nPlease check your ports or any strange programs running.\nEnter your Password to unlock keyboard.", "KeyInjection Detected",4096) # MB_SYSTEMMODAL = 4096 -- Always on top.
        return False;
    #Sneaky Policy
    elif (policy == "sneaky"):
        randdrop += 1 
        #Drop every 5th letter
        if (randdrop==7):
            randdrop = 0;
            return False;
        else:
            return True;

    #Logging Only Policy
    elif (policy == "log"):
        log(event)
        return True;


    #Normal Policy
    log(event)
    return False

#This is triggered every time a key is pressed
def KeyStroke(event):

    global threshold, keystroke_threshold, policy, password, pcounter
    global speed, keystroke_std, prevTime, i, history, intrusion,blacklist

    print (event.Key)
    print (event.Message)
    print ("Injected",event.Injected)
    
    if (event.Injected != 0 and allow_auto_type_software):
        print ("Injected by Software")
        return True;
    
    
    #If an intrusion was detected and we are password protecting
    #Then lockdown any keystroke and until password is entered
    if (policy == "paranoid" and intrusion):    
        print (event.Key)
        log(event);
        if pcounter < len(password):  # Check if pcounter is within the valid range
            if (password[pcounter] == chr(event.Ascii)):
                pcounter += 1;
                if (pcounter == len(password)):
                    win32ui.MessageBox("Correct Password!", "KeyInjection Detected",4096) # MB_SYSTEMMODAL = 4096 -- Always on top.
                    intrusion = False
                    pcounter = 0
        else:
            pcounter = 0

        return False


    #Initial Condition
    if (prevTime == -1):
        prevTime = event.Time;
        return True


    if (i >= len(history)): i = 0;

    #TypeSpeed = NewKeyTime - OldKeyTime
    history[i] = event.Time - prevTime
    print(event.Time, "-", prevTime, "=", history[i])
    prevTime = event.Time
    speed = sum(history) / float(len(history))
    time_diffs = [abs(history[(i-1)%size] - history[i%size]) for i in range(size)]
    keystroke_std = statistics.stdev(time_diffs)
    i = i + 1

    print("\rAverage Speed:", speed)
    print("\rKeystroke Consistency:", keystroke_std)
    
    #Blacklisting    
    for window in blacklist.split(","):
        if window in event.WindowName:
            return caught(event)

    #Intrusion detected
    if (speed < threshold) or (keystroke_std < keystroke_threshold):
        return caught(event)
    else:
        intrusion = False
    # pass execution to next hook registered 
    return True

# create and register a hook manager 
kl         = pyWinhook.HookManager()
kl.KeyDown = KeyStroke

# register the hook and execute forever
kl.HookKeyboard()
pythoncom.PumpMessages()
