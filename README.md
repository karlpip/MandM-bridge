# matrix2murmur

Bridges between a Murmurserver(currently listening on every channel) and a matrix channel. \
ICE is used to communicate with the murmur server, matrix-nio is used for matrix.

## Setup

Create a matrix user and create and join channel you want to bridge to.
Set the credentials and channel name in bridge.conf.

Activate ICE and configure the secret as described at https://wiki.mumble.info/wiki/Ice.
Fill in the murmur section in bridge.conf.

To run the script as a service you can use the provided service file, just change the paths before.