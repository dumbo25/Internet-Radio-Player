#!/usr/bin/env python3

#########################
#
# m3uCheck.py is a python3 script to validate m3u files downloaded
# from the internet. m3u files can be used for playlists and streaming
# radio stations. I would expect m3u files to conform to a standard
# format. However, there is no formal standard.
#
# Within the alarm clock project, m3u files are used as the definition
# of streaming internet radio stations, or as input to iRadioPlayer.py
#
# m3u are text files. Also, m3u files can be used for playlists by mpd.
#
# This description focuses on how I use m3u files are commonly used for 
# streaming radio stations, and how I am extending it for my use.
#
# Details about the m3u file format can be found here:
#
#    http://n4k3d.com/the-m3u-file-format/
#    https://en.wikipedia.org/wiki/M3U
#
# My description focuses on my interpretation of how m3u files are used
# to describe streaming radio:
#
#    line 1 is the file format descriptor and must start with: #EXTM3U
#
#    Subsequent lines come in pairs. For most streaming radio channels,
#    there are only 3 lines in an m3u file
#
#    line N (where N is an even number) must start with #EXTINF: followed
#    by a description of the streaming radio station
#
#    A song EXTINF entry would be something like:
#       #EXTINF:track,[min:sec,] artist - title
#
#    A station EXTINF has the format:
#       #EXTINF:-1,stationDescription
#
#       -1 indicates it is not a track, but a station
#
#    line N+1 is the streaming radio station
#
#    blank lines are ignored
#
# Often streaming radio m3u files downloaded from the internet do not contain
# lines 1 or 2. This script will repair those files.
#
# My extensions to m3u is to include my status of the m3u file. I want to find
# streaming radion m3u files download them to a Raspberry Pi and then check
# them. A check can result in one of the following states:
#    unchecked or no colon and no state
#    good - the file format is valid and the stream works
#    bad - the stream does not work
#    use - the stream works, and I like it and want it to use it
#    shelf - the stream works, but does not suit my tastes
#
# Once a file has been checked, it doesn't need to be checked again
#
# I add the state to the first line, using the format:
#
#    #EXTM3U: state
#
# Here are some examples:
#    This is an unchecked file
#       #EXTM3U
#    This file contains a working stream in standard m3u format
#       #EXTM3U: good
#
# I use three question (???) marks to indicate features that are not
# quite finished
#
# m3uCheck.py was tested on a Raspberry Pi 3 model B+ running raspbian
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
#    whether or not they work using m3uCheck.py
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
#          /etc/asound.conf
#          /use/share/alsa/alsa.conf
#          /home/pi/radio/iRadioPlayer.conf
#
#       Logs are stored here:
#          /var/log/mpd/mpd.log
#          /home/pi/radio/iRadioPlayer.log
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
#    python3 iRadioPlayer.py
#
# This command helps count number of files that are good:
#    cat *.m3u | grep "#EXTM3U: good" | wc -l
# 
# and this one shows the files that are good:
#    grep -iRl "#EXTM3U: good" *.m3u
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
import urllib.request

#########################
# Global Variables

fileLog = open('/home/pi/Stations/m3uCheck.log', 'w+')
currentStationConfig = '/home/pi/Stations/m3uCheck.conf'

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
# ??? if exit with x, then get currently playing song when restarting rather than
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
        fileSong = open(f, 'r')
        songAndTitle = fileSong.readline()
        i = songAndTitle.find("-") + 2
        songAndNewline = songAndTitle[i:]
        song = songAndNewline.rstrip()
        fileSong.close()
    except Exception as ex:
        printMsg("Exception in lastStation = [" + ex + "]")
        song = ""

    return song

def readiRadioPlayerConfig():
    global currentStation
    global currentVolume
    global currentPlaylist

    song = lastStation()

    try:
        f = open(currentStationConfig, 'r')
        songAndTitle = f.readline()
        if song == "":
            st = songAndTitle.rstrip()
            i = st.find("-") + 2
            song = st[i:]

        currentStation = song
        l = f.readline()
        v = l.rstrip()
        currentVolume = int(v)
        l = f.readline()
        currentPlaylist = l.rstrip()
        f.close()
    except Exception as ex:
        printMsg("Exception in readiRadioPlayerConfig [" + ex + "]")
        currentStation = ""
        currentVolume = defaultVolume
        currentPlaylist = defaultPlaylist
        f.close()

    printMsg("read iRadioPlayer config")
    printMsg(" song = [" + currentStation + "]")
    printMsg(" volume = [" + str(currentVolume) + "]")
    printMsg(" playlist = [" + currentPlaylist + "]")

    cmd = "rm " + tempStationFile
    subprocess.call(cmd, shell=True)
    return

def writeiRadioPlayerTxt():
    global currentStation

    # current song can be null
    o = subprocess.check_output("mpc current", shell=True)
    songAndTitle = o.decode("utf-8")
    if songAndTitle != "":
        songAndTitle = songAndTitle.rstrip()

    i = songAndTitle.find("-") + 2
    currentStation = songAndTitle[i:]

    f = open(currentStationConfig, 'w')
    f.write(currentStation + "\n")
    f.write(str(currentVolume) + "\n")
    f.write(currentPlaylist + "\n")
    f.close()

def init():
    readiRadioPlayerConfig()

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

    print("Loading songs takes a few minutes. Please wait for > prompt")
    for file in os.listdir(directoryMusic):
        if file.endswith(".m4a"):
            dirName = os.path.join(directoryMusic, file)
            fileName = "file://" + dirName
            cmd = 'mpc insert ' + '"' + fileName + '"'
            subprocess.call(cmd, shell=True)

    cmd = "mpc save " + playlist_name
    subprocess.call(cmd, shell=True)

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
    print ("Song Commands:")
    print ("   >[=n]  Play, where n is the song number")
    print ("          n is optional and by default plays the current song")
    print ("   !      Pause")
    print ("   p      Previous")
    print ("   n      Next")
    print ("Volume Commands:")
    print ("   m      Mute volume toggle")
    print ("   +      Increase volume")
    print ("   -      Decrease volume")
    print ("Playlist Commands:")
    print ("   a=f    Add song named f from Music directory to playlist")
    print ("          include .m4a extension. Do not escape or quote")
    print ("   d[=n]  Delete song numbered n from playlist")
    print ("          n is optional and the default is the current song")
    print ("   C      Current playlist")
    print ("   D      Delete all songs from the playlist")
    print ("   f=s    Find and play the first song containing the string s")
    print ("          escape spaces and other character with backslash")
    print ("   I[=n]  Initialize playlist from Music directory")
    print ("          n is optional and by default n = all_songs")
    print ("   L=n    Load playlist named n")
    print ("   P      List playlists")
    print ("   R[=n]  Remove playlist named n")
    print ("          n is optional and the default is current playlist")
    print ("   s[=s]  Show all songs or just songs containing the string s")
    print ("          escape spaces and other character with backslash")
    print ("   S[=n]  Save playlist named n")
    print ("          n is optional and the default is current playlist")
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
printMsg("Starting m3uCheck")

try:

    # this script should loop through m3u files in Stations directory
    #   if m3u file format is invalid, then
    #      prompt for description
    #      and rewrite valid format
    #   if status is not set, then
    #      read file and start playing the stream
    #      print menu and prompt for an action (use, shelf, skip, ...)
    #      if action changes state of m3u file then overwrite file

    # need to have terms to reject in a file: country, mraz, ... mark as shelf

    # need to check if station works


    # init()

    # this works, but how to know it works programmatically ?
    # cvlc http://av.rasset.ie/av/live/radio/radio1.m3u

    print("Checking m3u files ...")
    fileCount = 0
    for file in os.listdir(directoryStations):
        if file.endswith(".m3u"):
            fileName = os.path.join(directoryStations, file)
            lines = []
            i = 0
            w = True
            f = open(fileName, 'r')
            fileCount += 1
            print(str(fileCount) + ": " + fileName)
            for line in f:
                line = line.strip()
                if not line:
                    # skip blank lines
                    print("    skip blank lines")
                    continue
                elif line.startswith('#'):
                    if line.startswith('#EXTM3U:'):
                        # skip files that have already been checked
                        print("    skip files that have already been checked")
                        w = False
                        continue
                    elif line.startswith('#EXTM3U'):
                        if i == 0:
                            lines.append(line)
                            print("   " + line)
                            i += 1
                        else:
                            print("file does not start with #EXTM3U: " + line)
                            continue
                    elif line.startswith('#EXTINF:'):
                        if i == 1:
                            lines.append(line)
                            print("   " + line)
                            i += 1
                        else:
                            print("second line is not #EXTINF: " + line)
                            continue
                    else:
                        # skip other # lines as comments
                        print("skipping comments: " + line)
                        continue
                elif i == 2:
                    req = urllib.request.Request(line)
                    try:
                        response = urllib.request.urlopen(req)
                    except Exception as e:
                        print("    in except = " + str(e))
                        y = getattr(e, "reason", None)
                        if y is not None:
                            l = lines.pop(0)
                            n = l + ": unreachable"
                            lines.insert(0, n)
                            lines.append(line)
                            print("   " + line)
                            i += 1
                        else:
                            y = getattr(e, "code", None)
                            if y is not None:
                                l = lines.pop(0)
                                n = l + ": failed request"
                                lines.insert(0, n)
                            else:
                                l = lines.pop(0)
                                n = l + ": good"
                                lines.insert(0, n)
                            lines.append(line)
                            print("   " + line)
                            i += 1
                    else:
                        print("too many lines: " + line)
                        lines.append(line)
                        print("   " + line)
                        i += 1
                        continue
            f.close()

            if w:
                f = open(fileName, 'w')
                for line in lines:
                    f.write(line + '\n')
                f.close()

    print("Should be normal exit")
    sys_exit()

    ans = True
    while ans:
        printMenu()

        # command order was by type, but changed to alphabetic because it
        # is easier to find the command
        ans = input(">")
        if ans != "" and ans[0] == ">":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # play song number n
                s = ans[2:]
                print ("play song number " + s)
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
                    # add song
                    file = ans[2:]
                    print ("add song " + file)
                    dirName = os.path.join(directoryMusic, file)
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
                # delete song number n
                s = ans[2:]
                print ("delete song number " + s)
                cmd = "mpc del " + s + limitMPCoutput
                subprocess.call(cmd, shell=True)
            else:
                # play
                print("delete current song")
                cmd = "mpc del 0 " + limitMPCoutput
                subprocess.call(cmd, shell=True)
        elif ans == "D":
            if currentPlaylist == defaultPlaylist:
                print("Cannot delete all songs from default playlist")
            else:
                # Delete all songs from the playlist
                cmd = "mpc stop " + limitMPCoutput
                subprocess.call(cmd, shell=True)
                cmd = "mpc clear " + limitMPCoutput
                subprocess.call(cmd, shell=True)
        elif ans != "" and ans[0] == "f":
            ans2 = ans[1:]
            if ans2 != "" and ans[1] == "=":
                # find and play song containing string s
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
                # search songs in playlist containing string s
                print ("find and list songs matching a string (case sensitive)")
                s = ans[2:]
                cmd = "mpc playlist | grep -n " + s
                subprocess.call(cmd, shell=True)
            else:
                # list all songs in playlist
                print ("list all songs in playlist")
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
    printMsg("iRadioPlayer terminated")
    writeiRadioPlayerTxt()
    if ans == "x":
        printMsg("... Song still playing")
        fileLog.close()
    elif ans == "o":
        subprocess.call("mpc stop ", shell=True)
        printMsg("... Shutting down raspberry pi")
        fileLog.close()
        subprocess.call("sudo shutdown -h 0", shell=True)
    else:
        subprocess.call("mpc stop ", shell=True)
        fileLog.close()

