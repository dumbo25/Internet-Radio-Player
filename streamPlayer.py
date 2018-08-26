#!/usr/bin/env python3


#########################
#
# streamPlayer.py is a python3 script to play internet radio using mpd
# and mpc.
#
# One goal of writing this script was to understand how these commands
# could be used in a larger alarm clock radio project to play internet
# radio stations. Also, in working on the script and using the script,
# I was able to determine the features needed in the alarm clock. This
# was adapted from the streamPlayer.py script
#
# I use three question (???) marks to indicate features that are not quite
# finished
#
# streamPlayer.py was tested on a Raspberry Pi 3 model B+ running raspbian
# stretch
#
# This script requires the following:
#
#    $ sudo apt-get install mpc mpd -y
#    $ sudo apt-get alsa -y
#
#    HiFiBerry AMP 2 top board, barrel power supply and Speaker
#
#    alsamixer is used to set the digital volume to 20%
#
#    Finding working internet radio stations is difficult. The general idea
#    is to find m3u file types. Copy the m3u to stations and then validate
#    whether or not they work
#
#    Create a stations directory on MacBook. Copy m3u files from the internet.
#    The difficulty seems to be in finding streaming stations that work. Here
#    are some good sources:
#       https://github.com/jprjr/internet-radio-streams/tree/master/m3u/iheartradio/by-callletters
#       http://dir.xiph.org/by_genre/Rock
#
#    Copy or download the m3us from the sources above to MacBook. Copy the m3u files
#    from MacBook to Raspberry Pi using:
#       $ scp * pi@<your-hostname>:Stations/.
#
#    On Raspberry Pi
#
#       Config files:
#          /etc/mpd.conf
#          /use/share/alsa/alsa.conf
#          /home/pi/radio/streamPlayer.conf
#
#       Logs are stored here:
#          /var/log/mpd/mpd.log
#          /home/pi/radio/streamPlayer.log
#
#       MPD playlists won't work for streaming radio:
#          created a data structure to store a streaming playlist
#          mpd only keeps the stream. Want to search on the description
#
#       Stations are stored here:
#          /home/pi/Stations
#
#       MPD playlists are different than streaming radio station playlists.
#       Streaming radio playlists are stored here:
#          /home/pi/Stations/playlists
#
#       commands to control/examine mpd service
#          $ sudo service mpd stop
#          $ sudo service mpd start
#          $ sudo service --status-all | grep mpd
#
#       details of the mpc and mpd commands
#          man mpd
#          man mpc
#
# Start the script running using:
#    python3 streamPlayer.py
#
# Notes:
#    If music file name contains a backquote, you will get error message:
#       EOF in backquote substitution
#
#########################

import time
import datetime
import os
import sys
import subprocess

#########################
# Global Variables

fileLog = open('/home/pi/radio/streamPlayer.log', 'w+')
currentStationConfig = '/home/pi/radio/streamPlayer.conf'
tempStationFile = '/home/pi/radio/streamPlayer.tmp'
allStationsFile = '/home/pi/Stations/playlists/all_stations.m3u'

directoryStations = "/home/pi/Stations"
directoryPlaylist = "/home/pi/Stations/playlists"

defaultVolume = 60
currentVolume = defaultVolume

muteVolume = False

# mpd doesn't remember the current playlist
# so, mpc has no way to retrieve it
# if mpc commands are run outside of this script, then there is no
# way to find if the playlist changed
defaultPlaylist = "all_stations"
currentPlaylist = defaultPlaylist

# data structure to store radio stations: station, brief, long and stream
# mpd doesn't store enough meaningful information in the playlist
stationList = list()

# Instead of starting with the first station every time, remember last station
# played or get current station playing and start playing it
# ??? if exit with x, then get currently playing stream when restarting rather than
#     last known station to be playing ???
# currentStation is an index into stationList
currentStation = ""
cStation = 0

# On commands like play, prev and next, mpc outputs a line similar to:
#
#    volume: n/a repeat: off random: off single: off consume: off
#
# adding the following to any mpc command suppresses that output

limitMPCoutput = " | grep \"[-,'[']\""


#########################
# Log messages should be time stamped
def timeStamp():
    t = time.time()
    s = datetime.datetime.fromtimestamp(t).strftime('%Y/%m/%d %H:%M:%S - ')
    return s

# Write messages in a standard format
def printMsg(s):
    fileLog.write(timeStamp() + s + "\n")

def lastStation():
    f = tempStationFile
    cmd = "mpc current > " + f
    subprocess.call(cmd, shell=True)
    try:
        fileStation = open(f, 'r')
        stream = fileStation.readline()
        stream = stream.rstrip()
        fileStation.close()
    except Exception as ex:
        printMsg("Exception in lastStation = [" + ex + "]")
        stream = ""

    return stream

def readStreamPlayerConfig():
    global currentStation
    global currentVolume
    global currentPlaylist

    stream = lastStation()

    try:
        f = open(currentStationConfig, 'r')
        stream2 = f.readline()
        if stream2 == "":
            currentStation = stream
        else:
            currentStation = stream2.rstrip()

        l = f.readline()
        v = l.rstrip()
        currentVolume = int(v)
        l = f.readline()
        currentPlaylist = l.rstrip()
        f.close()
    except Exception as ex:
        printMsg("Exception in readStreamPlayerConfig [" + ex + "]")
        currentStation = ""
        currentVolume = defaultVolume
        currentPlaylist = defaultPlaylist
        f.close()

    printMsg("read streamPlayer config")
    printMsg(" stream = [" + currentStation + "]")
    printMsg(" volume = [" + str(currentVolume) + "]")
    printMsg(" playlist = [" + currentPlaylist + "]")

    cmd = "rm " + tempStationFile
    subprocess.call(cmd, shell=True)
    return

def incrementCurrentStation(i):
    global stationList
    global cStation

    last = len(stationList)
    cStation = cStation + i

    if cStation < 0:
        cStation = 0
    if cStation >= last:
        cStation = last-1

def switchStation(station):
    global stationList

    last = len(stationList)
    if station < 0:
        station = 0
    if station >= last:
        station = last-1

    cmd = 'mpc clear'
    subprocess.call(cmd, shell=True)

    stream = stationList[station][3]
    print("Station = " + stationList[station][0] + ", " + stationList[station][1])
    cmd = 'mpc insert "' + stream + '"' + limitMPCoutput
    subprocess.call(cmd, shell=True)

    cmd = "mpc play "  + limitMPCoutput
    subprocess.call(cmd, shell=True)

    return

def writeStreamPlayerTxt():
    global currentStation

    # current stream can be null
    o = subprocess.check_output("mpc current", shell=True)
    stream = o.decode("utf-8")
    if stream != "":
        stream = stream.rstrip()

    currentStation = stream

    f = open(currentStationConfig, 'w')
    f.write(currentStation + "\n")
    f.write(str(currentVolume) + "\n")
    f.write(currentPlaylist + "\n")
    f.close()

def init():
    global stationList

    # on start up initialize the station list
    stationList = list()

    # open all stations and fill in the stationList data structure
    f = open(allStationsFile, 'r')

    print("Loading stations")
    for line in f:
        line = line.strip()
        if line:
            # line is not blank
            l = line.split(',') 
            d = (l[0],l[1],l[2],l[3])
            stationList.append(d)

    f.close()

    readStreamPlayerConfig()

    print("volume = [" + str(currentVolume) + "]")
    cmd = "amixer set Digital " + str(currentVolume) + "%"
    subprocess.call(cmd, shell=True)

    if currentStation == "":
        cmd = "mpc play " + limitMPCoutput
        subprocess.call(cmd, shell=True)
    else:
        switchStation(cStation)
    return


def printMenu():
    print (" ")
    print ("Stream Commands:")
    print ("   >[=n]  Play, where n is the station number")
    print ("          n is optional and by default plays the current station")
    print ("   !      Pause")
    print ("   p      Previous")
    print ("   n      Next")
    print ("Volume Commands:")
    print ("   m      Mute volume toggle")
    print ("   +      Increase volume")
    print ("   -      Decrease volume")
    print ("Station Commands:")
    print ("   C      Current station")
    print ("   f=s    Find and play the first stream containing the string s")
    print ("          escape spaces and other character with backslash")
    print ("   s[=s]  Show all stations or just station descriptions containing the string s")
    print ("          escape spaces and other character with backslash")
    print ("Exit Commands")
    print ("   o      Shut raspberry pi off")
    print ("   x      Exit and leave music playing")
    print (" Return   Press Enter or Return key to exit and turn off music")

#########################

printMsg("Starting streamPlayer")
print("If after reboot, mpd loads last station or playlist. Please wait ...")

try:

    ans = True
    init()

    while ans:
        printMenu()

        # command order was by type, but changed to alphabetic because it
        # is easier to find the command
        ans = input(">")
        if ans != "" and ans[0] == ">":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # play station number n
                s = ans[2:]
                switchStation(int(s))
            else:
                # play
                print("play")
                cmd = "mpc play" + limitMPCoutput
                subprocess.call(cmd, shell=True)
        elif ans == "!":
            # pause
            print("pause")
            cmd = "mpc stop " + limitMPCoutput
            subprocess.call(cmd, shell=True)
        elif ans == "+":
            # volume up
            print ("volume up")
            currentVolume +=5
            if currentVolume > 100:
                currentVolume = 100
            cmd = "amixer set Digital " + str(currentVolume) + "%"
            subprocess.call(cmd, shell=True)
        elif ans == "-":
            # volume down
            print ("volume down")
            currentVolume -=5
            if currentVolume < 0:
                currentVolume = 0
            cmd = "amixer set Digital " + str(currentVolume) + "%"
            subprocess.call(cmd, shell=True)
        elif ans == "C":
            # Display current station
            s = stationList[cStation][0]
            print("Station playing = " + s)
            s = stationList[cStation][1]
            print("Description     = " + s)
        elif ans != "" and ans[0] == "f":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # find and play station description containing string t
                t = ans[2:]
                print("find and play station containing " + t)
                i = 0
                for s in stationList:
                    # if t in s[1]
                    if t in s[1]:
                        print (str(i) + ": " + s[0] + ", " + s[1])
                        switchStation(i)
                        cStation = i
                        break
                    i += 1
            else:
                print("f requires a string")
        elif ans == "m":
            # mute
            muteVolume = not muteVolume
            if muteVolume == True:
                print ("mute")
                previousVolume = currentVolume
                currentVolume = 0
                cmd = "amixer set Digital " + str(currentVolume) + "%"
            else:
                print ("unmute")
                currentVolume = previousVolume
                cmd = "amixer set Digital " + str(currentVolume) + "%"
            subprocess.call(cmd, shell=True)
        elif ans == "n":
            # next
            print("next")
            incrementCurrentStation(1)
            switchStation(int(cStation))
        elif ans == "o":
            # shutoff raspberry pi and radio
            sys.exit()
        elif ans == "p":
            # previous
            print("previous")
            incrementCurrentStation(-1)
            switchStation(int(cStation))
        elif ans != "" and ans[0] == "s":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # search brief description in stationList to find string t
                print ("find and list streams matching a string (case sensitive)")
                t = ans[2:]
                # list all stations
                i = 0
                for s in stationList:
                    # if t in s[1]
                    if t in s[1]:
                        print (str(i) + ": " + s[0] + ", " + s[1])
                    i += 1
            else:
                # list all stations
                i = 0
                for s in stationList:
                    print (str(i) + ": " + s[0] + ", " + s[1])
                    i += 1
        elif ans == "x":
            # exit and leave music playing
            sys.exit()
        elif ans == "":
            # exit and stop music
            sys.exit()
        else:
            print("Unrecognized command: " + ans)

    sys.exit()

except KeyboardInterrupt: # trap a CTRL+C keyboard interrupt
    printMsg("keyboard exception occurred")

except Exception as ex:
    printMsg("ERROR: an unhandled exception occurred: " + str(ex))

finally:
    printMsg("streamPlayer terminated")
    writeStreamPlayerTxt()
    if ans == "x":
        printMsg("... Stream still playing")
        fileLog.close()
    elif ans == "o":
        subprocess.call("mpc stop ", shell=True)
        printMsg("... Shutting down raspberry pi")
        fileLog.close()
        subprocess.call("sudo shutdown -h 0", shell=True)
    else:
        subprocess.call("mpc stop ", shell=True)
        fileLog.close()

