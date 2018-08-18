# Internet-Radio-Player
Raspberry Pi 3 internet radio player using python3 script

I am creating a Radio Alarm Clock, which has many features. One feature is the ability to play streaming radio stations. I didn't know what features would be required for a streaming player, and so created this script and played with it for a while to ensure it had everything I needed.

I don't consider this a finished script for people to use, but if someone wants to play around with streaming radio stations it is a fairly good start.

Eventually the featues of this script will be folded into my Alarm Clock Radio's GUI.

More detailed instructions can be found here: https://sites.google.com/site/cartwrightraspberrypiprojects/song-player

I use two directories on the Raspberry Pi:
* /home/pi/Stations
* /home/pi/radio

m3uCheck.py and m3uGet.sh should be in /home/pi/Stations. These aren't finished scripts, butt hey get the job done. m3uGet.sh downloads a whole bunch of streaming radio stations, but many of these no longer work. So, m3uCheck.py determines if the station is reachable or not.

I also extend m3u files to include information useful to my streaming player.

streamPlayer.py should be in /home/pi/radio
