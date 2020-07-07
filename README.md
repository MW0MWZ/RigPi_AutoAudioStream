# RigPi_AutoAudioStream
Auto Audio Streamer Service

This python script is setup to stream an audio stream out using ffmpeg, you will need somthing to handle it on the other end, but this will get the stream from the RigPi and send it wherever you like.

It also intigrates with HRDLog.net so that you can use that banner for showing the online/offline status of the stream, and the frequency (and radio information).

See the variables set in the top of the python script.
Put the Python script in /usr/local/sbin
Put the SystemD unit file in /etc/systemd/system

Maks eusre you have arecord and ffmpeg installed.

apt-get install ffmpeg python-mysql.connector
