# 10cord
**10cord** is a **Discord alternative client** as a **Command Line Interface (CLI) application**. Yes, it is **against Discord's TOS**, but it is a fun project to work on. It is written in Python, and only uses HTTP requests to communicate with Discord's API.

By using **10cord**, you can safely talk with your friends on Discord in your company's open space, without having to worry about your boss seeing that you're not working. You will just look like a hacker, and that's cool.

## Installation
```bash
git clone https://github.com/MCXIV/10cord.git
cd 10cord
python3 -m pip install -r requirements.txt
```

### Optional
If you want to display images and videos in your terminal, you can install [chafa](https://github.com/hpjansson/chafa)

**Be careful, 10cord automatically downloads any attachments if you enabled them.**

```bash
# Arch Linux
yay -S chafa
sudo pacman -S chafa

# Debian
sudo apt install chafa
```

## Usage
```bash
python3 src/10cord.py -h

usage: 10cord.py [-h] [-a ATTACH] email password channel

positional arguments:
  email                 User email
  password              User password
  channel               Channel ID to get messages from

options:
  -h, --help            show this help message and exit
  -a ATTACH, --attach ATTACH
                        If true, displays attachments (Requires chafa)

python3 src/10cord.py $EMAIL $PASSWORD $CHANNEL
```

### Internal commands
- `:q` to quit the application
- `:attach:<path>:<content>` to send an attachment. `<path>` is the path to the file, and `<content>` is the message to send with the attachment. If `<content>` is empty, the attachment will be sent without any message.
- `:cr` to refresh the screen
- `:help` to display the help message

## Demo
![demo example](docs/demo.gif "Demo example")

## Features
- login
- get messages from a specific channel
- send messages to a specific channel (just type your message and press enter)
- attachments (images and videos) are displayed as links. Ctrl + click on the link to open it in your browser. If chafa is installed, the attachment will be printed into your terminal. (Posix only)
