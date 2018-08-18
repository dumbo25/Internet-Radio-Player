#!/usr/bin/env python3


#########################
#
# streamPlayer.py is a python3 script to play internet radio using mpd
# and mpc. Stations are stored in the directory /home/pi/Stations
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
#       Playlists are stored here:
#          /var/lib/mpd/playlists
#
#       Stations are stored here:
#          /home/pi/Stations
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

directoryStations = "/home/pi/Stations"

defaultVolume = 60
currentVolume = defaultVolume

muteVolume = False

# mpd doesn't remember the current playlist
# so, mpc has no way to retrieve it
# if mpc commands are run outside of this script, then there is no
# way to find if the playlist changed
defaultPlaylist = "all_stations"
currentPlaylist = defaultPlaylist

# Instead of starting with the first station every time, remember last station
# played or get current station playing and start playing it
# ??? if exit with x, then get currently playing stream when restarting rather than
#     last known station to be playing ???
currentStation = ""

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
    readStreamPlayerConfig()

    print("volume = [" + str(currentVolume) + "]")
    cmd = "amixer set Digital " + str(currentVolume) + "%"
    subprocess.call(cmd, shell=True)

    if currentStation == "":
        cmd = "mpc play " + limitMPCoutput
    else:
        cmd = 'mpc searchplay title "' + currentStation + '"' + limitMPCoutput

    subprocess.call(cmd, shell=True)
    return

# Insert music from my Apple library into mpd and save it as a playlist
def initPlaylist(playlist_name):
    global currentPlaylist

    cmd = "mpc clear" + limitMPCoutput
    subprocess.call(cmd, shell=True)

    fileCount = 0

    print("Loading streams takes a few minutes. Please wait for > prompt")
    for file in os.listdir(directoryStations):
        if file.endswith(".m3u"):
            fileName = os.path.join(directoryStations, file)
            print(str(fileCount) + ": " + fileName)
            i = 0
            good = False
            f = open(fileName, 'r')
            for line in f:
                line = line.strip()
                print("   line = " + line)
                if line:
                    # line is not blank
                    if line.startswith('#'):
                        if i == 0:
                            if line.startswith('#EXTM3U: good'):
                                good = True
                        i += 1
                    elif i == 2:
                        # line 2 is the station
                        if good:
                            fileCount += 1
                            print(str(fileCount) + ": " + fileName)
                            cmd = 'mpc insert ' + '"' + line + '"'
                            subprocess.call(cmd, shell=True)

            f.close()

    currentPlaylist = playlist_name
    return

def removePlaylist(p):
    if p == defaultPlaylist:
        print("Cannot remove default playlist: " + defaultPlaylist)
    else:
        print ("Stopping ...")
        cmd = "mpc stop " + limitMPCoutput
        subprocess.call(cmd, shell=True)
        print("Remove playlist " + p)
        cmd = "mpc rm " + p + limitMPCoutput
        subprocess.call(cmd, shell=True)
        cmd = "mpc clear --wait " + limitMPCoutput
        subprocess.call(cmd, shell=True)

        initPlaylist(defaultPlaylist)


def printMenu():
    print (" ")
    print ("Stream Commands:")
    print ("   >[=n]  Play, where n is the stream number")
    print ("          n is optional and by default plays the current stream")
    print ("   !      Pause")
    print ("   p      Previous")
    print ("   n      Next")
    print ("Volume Commands:")
    print ("   m      Mute volume toggle")
    print ("   +      Increase volume")
    print ("   -      Decrease volume")
    print ("Playlist Commands:")
    print ("?   a=f    Add stream named f from Stations directory to playlist")
    print ("          include .m3u extension. Do not escape or quote")
    print ("??   d[=n]  Delete stream numbered n from playlist")
    print ("          n is optional and the default is the current stream")
    print ("   C      Current playlist")
    print ("   D      Delete all streams from the playlist")
    print ("   f=s    Find and play the first stream containing the string s")
    print ("          escape spaces and other character with backslash")
    print ("          ??? f=s is broken")
    print ("??   I[=n]  Initialize playlist from Stations directory")
    print ("          n is optional and by default n = all_stations")
    print ("??? need a better description of the station ???")
    print ("?   L=n    Load playlist named n")
    print ("           ??? L=n does what I is supposed to do ") 
    print ("   P      List playlists")
    print ("   R[=n]  Remove playlist named n")
    print ("          n is optional and the default is current playlist")
    print ("   s[=s]  Show all streams or just streams containing the string s")
    print ("          escape spaces and other character with backslash")
    print ("          ??? this need to work on descriptive names and not stream")
    print ("   S[=n]  Save playlist named n")
    print ("          n is optional and the default is current playlist")
    print ("          ??? S by itself does not work ")
    print ("Exit Commands")
    print ("   o      Shut raspberry pi off")
    print ("   x      Exit and leave music playing")
    print (" Return   Press Enter or Return key to exit and turn off music")
    print (" ??? mpd.config has errors in /var/log/mpd/mpd.log ???")
    print (" ???   alsa_mixer: Failed to read mixer for amixer: no such mixer ...")
    print (" ???   output: Failed to open mixer for amixer")
    print (" ???   ffmpeg/mov,mp4,m4a,3gp,3g2,mj2: stream 0, timescale not set ")
    print (" ???   ffmpeg/aac: Could not update timestamps for skipped samples ")

#########################

printMsg("Starting streamPlayer")
print("If after reboot, mpd loads last playlist. Please wait ...")

try:

    init()

    ans = True
    while ans:
        printMenu()

        # command order was by type, but changed to alphabetic because it
        # is easier to find the command
        ans = input(">")
        if ans != "" and ans[0] == ">":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # play stream number n
                s = ans[2:]
                print ("play stream number " + s)
                cmd = "mpc play " + s  + limitMPCoutput
                subprocess.call(cmd, shell=True)
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
        elif ans != "" and ans[0] == "a":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                try:
                    # add stream
                    file = ans[2:]
                    print ("add stream " + file)
                    dirName = os.path.join(directoryStations, file)
                    fileName = "file://" + dirName
                    # Use add to add to end rather than insert which puts after current
                    cmd = 'mpc add ' + '"' + fileName + '"'
                    print(cmd)
                    subprocess.call(cmd, shell=True)
                except Exception as ex:
                    printMsg("ERROR: an unhandled exception occurred: " + str(ex))
                    print ("Add failed for: " + fileName)
        elif ans == "C":
            # Display current playlist
            print("Current playlist = " + currentPlaylist)
        elif ans != "" and ans[0] == "d":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # delete stream number n
                s = ans[2:]
                print ("delete stream number " + s)
                cmd = "mpc del " + s + limitMPCoutput
                subprocess.call(cmd, shell=True)
            else:
                # play
                print("delete current stream")
                cmd = "mpc del 0 " + limitMPCoutput
                subprocess.call(cmd, shell=True)
        elif ans == "D":
            if currentPlaylist == defaultPlaylist:
                print("Cannot delete all streams from default playlist")
            else:
                # Delete all streams from the playlist
                cmd = "mpc stop " + limitMPCoutput
                subprocess.call(cmd, shell=True)
                cmd = "mpc clear " + limitMPCoutput
                subprocess.call(cmd, shell=True)
        elif ans != "" and ans[0] == "f":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # find and play stream containing string s
                print("find and play")
                s = ans[2:]
                cmd = "mpc searchplay title " + s
                subprocess.call(cmd, shell=True)
            else:
                print("f requires a string")
        elif ans != "" and ans[0] == "I":
            # initialize playlist
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                n = ans[2:]
            else:
                n = defaultPlaylist
            initPlaylist(n)
            currentPlaylist = n
        elif ans != "" and ans[0] == "L":
            # Load playlist
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                n = ans[2:]
                initPlaylist(n)
                currentPlaylist = n
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
            cmd = "mpc next " + limitMPCoutput
            subprocess.call(cmd, shell=True)
        elif ans == "o":
            # shutoff raspberry pi and radio
            sys.exit()
        elif ans == "p":
            # previous
            print("previous")
            cmd = "mpc prev " + limitMPCoutput
            subprocess.call(cmd, shell=True)
        elif ans == "P":
            # List all playlists
            cmd = "mpc lsplaylists"
            subprocess.call(cmd, shell=True)
        elif ans != "" and ans[0] == "R":
            # Remove playlist
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                n = ans[2:]
                removePlaylist(n)
            else:
                removePlaylist(currentPlaylist)
        elif ans != "" and ans[0] == "s":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # search streams in playlist containing string s
                print ("find and list streams matching a string (case sensitive)")
                s = ans[2:]
                cmd = "mpc playlist | grep -n " + s
                subprocess.call(cmd, shell=True)
            else:
                # list all streams in playlist
                print ("list all streams in playlist")
                cmd = "mpc playlist | grep -n '-'"
                subprocess.call(cmd, shell=True)
        elif ans != "" and ans[0] == "S":
            # Save playlist
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # Save playlist as n
                n = ans[2:]
                print ("save playlist as " + n)
                cmd = "mpc save " + n
                subprocess.call(cmd, shell=True)
            else:
                # Save current playlist
                print ("save current playlist")
                cmd = "mpc save " + currentPlaylist + limitMPCoutput
                subprocess.call(cmd, shell=True)
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

