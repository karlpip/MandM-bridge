# MandM-bridge

Bridges between a Murmur server and a matrix channel.\
ICE is used to communicate with the murmur server, matrix-nio is used for matrix.

## Features

- [X] Bridge text messages.
- [X] Implement optional message handlers to easily modify, filter and save messages before bridging.
  - [X] Configure which handler should be active in config file.
  - [X] Handler: Dont bridge botamusique (https://github.com/azlux/botamusique, check it out!) messages.
  - [X] Handler: Delete html tags from links postged in mumble.
- [ ] Bridge images.
  - [X] Bridge images from matrix to mumble
  - [ ] Bridge images from mumble to matrix
- [X] Make bridged murmur channels configurable.
- [X] Bridge mumble join / leave events.
- WIP: [ ] End to end encryption


## Setup

Clone the repository and checkout the latest tag.

### Python virtual environment (optional)

To create a python virtual environment execute the following in the repo directory: \
`python3 -m venv env`

And then activate the environment with: \
`source env/bin/activate`

### Dependencies

Install the needed python packages with: \
`pip3 install -r requirements.txt`

### Configuration

Create a matrix user and create and join channel you want to bridge to.
Set the credentials and channel name in bridge.conf.

Activate ICE and configure the secret as described at https://wiki.mumble.info/wiki/Ice.
Fill in the murmur section in bridge.conf.

To send bigger images to murmur you have to set: \
`imagemessagelength=0` \
In your mumble.ini. This disables the length limit of messages containing images.

### Running

You can execute the bot like this:
`python3 main.py`

Or to run the script as a service you can use the provided service file under `examples/`, dont forget to set the paths accordingly.

## Licencse

Copyright 2022 Karl Piplies

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
