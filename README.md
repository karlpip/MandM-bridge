# matrix2murmur

Bridges between a Murmurserver(currently listening on every channel) and a matrix channel. \
ICE is used to communicate with the murmur server, matrix-nio is used for matrix.

## Features

- [X] Bridge text messages.
- [ ] Implement optional message handlers to easily modify, filter and save messages before bridging.
  - [ ] Configure which handler should be active in config file.
  - [X] Handler: Dont bridge private mumble messages
  - [X] Handler: Dont bridge botamusique (https://github.com/azlux/botamusique, check it out!) messages.
  - [X] Handler: Delete html tags from links postged in mumble
- [ ] WIP: Bridge images.

## Setup

TODO: add requirements.txt for python3 env setup.

Create a matrix user and create and join channel you want to bridge to.
Set the credentials and channel name in bridge.conf.

Activate ICE and configure the secret as described at https://wiki.mumble.info/wiki/Ice.
Fill in the murmur section in bridge.conf.

To run the script as a service you can use the provided service file, just change the paths before.

## Licencse

Copyright 2022 Karl Piplies

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
