# -*- coding: utf-8 -*-
# --------------------------------------------------
# 10cord.py - A Discord client, entirely in your terminal.
# Quentin Dufournet, 2023
# --------------------------------------------------
# Built-in
import os
import json
import time
import argparse
import threading
import sys
import subprocess as sp

# 3rd party
from emoji import EMOJI_DATA
import requests
import fake_useragent
from rich import print as rprint

# --------------------------------------------------


def parse_args():
    """
    The `parse_args` function is used to parse command line arguments for the user's email,
    password, and channel ID.

    :return: The function `parse_args()` returns the parsed command-line arguments as an
    `argparse.Namespace` object.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'email',
        help='User email',
    )
    parser.add_argument(
        'password',
        help='User password',
    )
    parser.add_argument(
        '-c', '--channel',
        help='Channel ID to get messages from',
        default=None
    )
    parser.add_argument(
        '-a', '--attach',
        help='Displays attachments (Requires chafa)',
        action='store_true'
    )
    parser.add_argument(
        '-t', '--token',
        help='Custom user token',
        default=None
    )

    return parser.parse_args()


class MyClient():
    def __init__(self) -> None:
        self.args = parse_args()
        self.url = 'https://discord.com/api/v9'

        if not os.path.exists('tmp'):
            os.mkdir('tmp')

        if not self.args.token:
            if os.path.exists('tmp/token.json'):
                with open('tmp/token.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_id = data['user_id']
                    self.token = data['token']
                    self.timestamp = data['timestamp']
                if float(self.timestamp) + 3600 < time.time():
                    self.login()
            else:
                self.login()

        self.headers = {
            'User-Agent': fake_useragent.UserAgent().random,
            'Authorization': self.args.token if self.args.token else self.token
        }

        if self.args.token:
            self.user_id = self.get_my_id()

        self.ids = {}
        self.attachments = []

    def get_my_id(self):
        """
        The function `get_my_id` retrieves the user ID associated with the token from the
        Discord API.

        :return: the user ID associated with the token.
        """

        response = requests.get(
            f'{self.url}/users/@me',
            headers=self.headers,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(
                f'Get my ID failed : {response.status_code} {response.text}')

        return response.json()['id']

    def login(self):
        """
        The `login` function sends a POST request to a specified URL with login credentials,
        and if
        successful, saves the user ID, token, and timestamp to a JSON file.
        """

        data = {
            'login': self.args.email,
            'password': self.args.password,
            'undelete': False,
            'login_source': None,
            'gift_code_sku_id': None
        }

        response = requests.post(
            f'{self.url}/auth/login',
            json=data,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(
                f'Login failed : {response.status_code} {response.text}')

        self.user_id = response.json()['user_id']
        self.token = response.json()['token']
        self.timestamp = str(time.time())

        with open('tmp/token.json', 'w', encoding='utf-8') as f:
            json.dump({'user_id': self.user_id, 'token': self.token,
                      'timestamp': self.timestamp}, f, indent=4)

    def get_messages(self):
        """
        The function `get_messages` retrieves the latest 100 messages from a specified
        channel using the Discord server.

        :return: a list of messages.
        """

        params = {
            'limit': '100',
        }

        response = requests.get(
            f'{self.url}/channels/{self.args.channel}/messages',
            params=params,
            headers=self.headers,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(
                f'Get messages failed : {response.status_code} {response.text}')

        messages = response.json()
        messages.reverse()

        return messages

    def manage_mentions(self, content):
        """
        The function `manage_mentions` replaces user mentions, the
        `@everyone` mention, and the `@here` mention in a given
        content with formatted text.

        :param content: The `content` parameter is a string that
        represents the content of a message
        :return: the modified content after managing mentions.
        """

        if '<@' in content and '<@&' not in content:
            # TODO: rework this part to avoid request as mentions is located
            # in the message requests
            user_id = content.split('<@')[1].split('>')[0]
            if user_id not in self.ids:
                self.ids[user_id] = self.get_username_from_id(user_id)
            username_in_content = self.ids[user_id]
            content = content.replace(
                f'<@{user_id}>', f'[bold][dark_orange]@{username_in_content}[/dark_orange][/bold]')
        if '@everyone' in content:
            content = content.replace(
                '@everyone', '[bold][dark_orange]@everyone[/dark_orange][/bold]')
        if '@here' in content:
            content = content.replace(
                '@here', '[bold][dark_orange]@here[/dark_orange][/bold]')

        return content

    def manage_attachments(self, content, message):
        """ Manage attachments in a message (Download, display, etc.)

        :param content: The `content` parameter is a string that
        represents the content of a message
        :param message: The `message` parameter is a dict that
        represents the message object
        :return: the modified content after managing attachments.
        """

        if message['attachments'] != []:
            content += (
                f'[bold][red]{message["attachments"][0]["url"]}[/red][/bold]'
            ) if content == '' else (
                f'\n[bold][red]{message["attachments"][0]["url"]}[/red][/bold]'
            )

            if message['attachments'][0]['url'] not in self.attachments:
                if self.args.attach:
                    file = requests.get(
                        message['attachments'][0]['url'], headers=self.headers
                    )
                    if file.status_code == 200:
                        with open(f'./tmp/{message["attachments"][0]["filename"]}', 'wb') as f:
                            f.write(file.content)
                        self.attachments.append(
                            message['attachments'][0]['url']
                        )

        return content

    def manage_referenced_message(self, content, message):
        """ Manage referenced message in a message

        :param content: The `content` parameter is a string that
        represents the content of a message
        :param message: The `message` parameter is a dict that
        represents the message object
        :return: the modified content after managing referenced message.
        """

        try:
            referenced_message = message['referenced_message']['content']
            referenced_message = self.manage_mentions(referenced_message)
            referenced_message = self.manage_attachments(
                referenced_message, message['referenced_message'])
            content += f'\n> [italic]{referenced_message}[/italic]'
        except KeyError:
            referenced_message = None

        return content

    def print_messages(self, messages):
        """
        The function "print_messages" takes in a list of messages and prints them.

        :param messages: The "messages" parameter is a list of messages that you want to
        print
        """

        for message in messages:
            date = message['timestamp'].replace('T', ' - ').split('.')[0]
            username = message['author']['username']
            content = message['content']
            content = self.manage_mentions(content)
            content = self.manage_attachments(content, message)
            content = self.manage_referenced_message(content, message)

            rprint(
                f'[bold][blue][{date}][/blue] [magenta]{username}[/magenta][/bold] : {content}')

            if message['attachments'] != [] and self.args.attach:
                if os.name == 'posix' and 'Chafa version' in sp.getoutput('chafa --version'):
                    os.system(
                        f'chafa ./tmp/{message["attachments"][0]["filename"]} --size=50x50 --animate=off'
                    )

    def diff_messages(self, messages1, messages2):
        """
        The function `diff_messages` takes two lists of messages and returns a new list
        containing messages that are in the first list but not in the second list.

        :param messages1: A list of messages
        :param messages2: An other list of messages

        :return: a list of messages that are present in `messages1` but not in `messages2`.
        """

        new_messages = []
        for message in messages1:
            if message not in messages2:
                new_messages.append(message)

        return new_messages

    def send_message(self, content, attachments=[]):
        """
        The `send_message` function sends a message to a specified channel using the
        Discord API.

        :param content: Message content that you want to send.

        :return: the JSON response from the API call.
        """

        data = {
            'content': content,
            'attachments': attachments
        }

        response = requests.post(
            f'{self.url}/channels/{self.args.channel}/messages',
            headers=self.headers,
            json=data,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(
                f'Send message failed : {response.status_code} {response.text}')

        self.refresh_screen()

        return response.json()

    def get_username_from_id(self, user_id):
        """
        The function `get_username_from_id` retrieves the username associated with a
        given user ID from the Discord API.

        :param user_id: Unique identifier of a user.

        :return: the username of the user with the given user_id if the response status
        code is 200. Otherwise, it returns the user_id itself.
        """

        response = requests.get(
            f'{self.url}/users/{user_id}',
            headers=self.headers,
            timeout=5
        )

        if response.status_code != 200:
            if 'rate limited' in response.text:
                time.sleep(1)
                return self.get_username_from_id(user_id)
            return user_id

        return response.json()['username']

    def request_upload_attachment(self, path, size):
        """
        This function requests an upload link for a file to a specified channel using
        the Discord API.

        :param path: Path of the file you want to send.
        :param size: Size of the file you want to send.

        :return: the JSON response from the API call.
        """

        data = {
            'files': [
                {
                    'filename': path,
                    'file_size': size,
                },
            ],
        }

        response = requests.post(
            f'{self.url}/channels/{self.args.channel}/attachments',
            headers=self.headers,
            json=data,
        )

        if response.status_code != 200:
            raise Exception(
                f'Put attachment failed : {response.status_code} {response.text}')

        return response.json()

    def upload_attachment(self, path, link, filename):
        """
        This function uploads a file to a specified channel using the Discord API.

        :param path: Path of the file you want to send.
        :param link: Upload link of the file you want to send.
        :param filename: Name of the file in Discord storage.

        :return: 1 if the upload was successful.
        """

        params = {
            'upload_id': link.split('upload_id=')[1]
        }

        with open(path, 'rb') as f:
            data = f.read()

        response = requests.put(
            f'https://discord-attachments-uploads-prd.storage.googleapis.com/{filename}',
            params=params,
            headers=self.headers,
            data=data,
        )

        if response.status_code != 200:
            raise Exception(
                f'Put attachment failed : {response.status_code} {response.text}')

        return 1

    def put_attachment(self, path, size, content):
        """
        This function sends a file to a specified channel using the Discord API.

        :param path: The `path` parameter is the path of the file you want to send.
        :param size: The `size` parameter is the size of the file you want to send.
        :param content: The `content` parameter is the message content that you want
        to send.

        :return: Nothing if the file can't be found.
        """

        if not os.path.isfile(path):
            rprint(f'[bold][red]Is {path} a file?[/red][/bold]')
            return

        request_attachment = self.request_upload_attachment(path, size)
        upload_link = request_attachment['attachments'][0]['upload_url']
        upload_filename = request_attachment['attachments'][0]['upload_filename']
        self.upload_attachment(path, upload_link, upload_filename)

        attachment_data = [
            {
                'id': '0',
                'filename': path,
                'uploaded_filename': upload_filename,
            },
        ]

        self.send_message(content, attachment_data)

    def list_friends(self):
        """ Get friends from Discord API """

        response = requests.get(
            f'{self.url}/users/@me/channels',
            headers=self.headers,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(
                f'Get friends failed : {response.status_code} {response.text}')

        list_friends = [element for element in response.json()
                        if element['type'] == 1]
        self.friends = list_friends

    def list_guilds(self):
        """ Get guilds's user from Discord API """

        response = requests.get(
            f'{self.url}/users/@me/guilds',
            headers=self.headers,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(
                f'Get guilds failed : {response.status_code} {response.text}')

        self.guilds = response.json()

        for guild in self.guilds:
            self.list_channels_from_guild(guild['id'])

    def rprint_friends(self):
        """ Print friends in a rich format """

        content = ''
        local_id = 0

        for friend in self.friends:
            local_id += 1
            friend_print = f'|  [#E01E5A]{local_id}[/#E01E5A] - ' + \
                f'{friend["recipients"][0]["username"]} - {friend["id"]}'
            friend_length = len(friend_print.replace(
                '[#E01E5A]', '').replace('[/#E01E5A]', ''))

            # Emoji or Special char. are 2 chars long
            for char in friend["recipients"][0]["username"]:
                if char in EMOJI_DATA:
                    friend_length += 1

            if friend_length > 80:
                friend_print = friend_print.replace(
                    friend["recipients"][0]["id"],
                    friend["recipients"][0]["id"][:80 -
                                                  friend_length - 8] + '...'
                )
                friend_length = len(friend_print.replace(
                    '[#E01E5A]', '').replace('[/#E01E5A]', '')) + 1

            friend_print += ' ' * \
                (80 - friend_length) + '|\n'

            self.friends[self.friends.index(friend)]['local_id'] = local_id

            content += friend_print

        content += '================================================================================='

        return content

    def list_channels_from_guild(self, guild_id):
        """ Get channels from a guild

        :param guild_id: the id of the guild you want to get channels from
        """

        response = requests.get(
            f'{self.url}/guilds/{guild_id}/channels',
            headers=self.headers,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(
                f'Get channels failed : {response.status_code} {response.text}')

        list_channels = [channel for channel in response.json()
                         if channel['type'] == 0]
        self.guilds[self.guilds.index(
            [guild for guild in self.guilds if guild['id'] == guild_id][0])]['channels'] = list_channels

    def rprint_guilds(self):
        """ Print guilds and channels in a rich format """

        # TODO: Rework or idk, the code looks horrible af
        content = ''
        local_id = 0

        for guild in self.guilds:
            guild_print = f'|  - {guild["name"]} -'
            if guild['owner']:
                guild_print += ' [#E01E5A](owner)[/#E01E5A]'

            guild_length = len(guild_print.replace(
                '[#E01E5A]', '').replace('[/#E01E5A]', '')
            )

            if guild_length < 80:
                guild_print += ' ' * \
                    (80 - guild_length) + '|\n'

            content += guild_print

            for channel in self.guilds[self.guilds.index(guild)]['channels']:
                local_id += 1
                channel_print = f'|     [#E01E5A]{local_id}[/#E01E5A] - {channel["name"]} - {channel["id"]}'
                channel_length = len(channel_print.replace(
                    '[#E01E5A]', '').replace('[/#E01E5A]', ''))

                # Emoji or Special char. are 2 chars long
                for char in channel['name']:
                    if char in EMOJI_DATA or char in ['｜']:
                        channel_length += 1

                if channel_length > 80:
                    channel_print = channel_print.replace(
                        channel['name'], channel['name'][:80 - channel_length - 8] + '...')
                    channel_length = len(channel_print.replace(
                        '[#E01E5A]', '').replace('[/#E01E5A]', '')) + 1

                channel_print += ' ' * \
                    (80 - channel_length) + '|\n'

                self.guilds[self.guilds.index(guild)]['channels'][self.guilds[self.guilds.index(guild)]['channels'].index(
                    channel)]['local_id'] = local_id

                content += channel_print

        content += '================================================================================='

        return content

    def refresh_screen(self):
        """ Refresh the screen and print the last messages """

        os.system('clear') if os.name == 'posix' else os.system('cls')
        self.messages = []
        new_messages = self.get_messages()
        diff_messages = self.diff_messages(new_messages, self.messages)
        self.print_messages(diff_messages)
        self.messages = new_messages

    def internal_command(self, command):
        """
        The `internal_command` function is used to execute internal commands.

        :param command: The `command` parameter is the command you want to execute.
        """

        if command == ':help':
            rprint()
            rprint('[#7289DA]' +
                   '==============================\n' +
                   '|[#E01E5A]       Commands list:       [/#E01E5A]|\n' +
                   '==============================\n'
                   '| :help - Show this help     |\n' +
                   '| :q - Exit 10cord           |\n' +
                   '| :attach - Attach a file    |\n' +
                   '| :cr - Clear and Refresh    |\n' +
                   '| :li - List Guilds & Chan.|\n'
                   '| :fr - List Friends    |\n'
                   '| :we - Print welcome message|\n'
                   '=============================='
                   '[/#7289DA]'
                   )
            rprint()

        elif command == ':q':
            if self.running:
                self.kill_thread = True
                self.main_loop_thread.join()
            self.clean()
            sys.exit()

        elif command == ':cr':
            self.refresh_screen()

        elif ':attach:' in command:
            attachment = command.split(':')[2]
            if len(command.split(':')) == 4:
                content = command.split(':')[3]
            else:
                content = ''
            if os.path.exists(attachment):
                self.put_attachment(
                    attachment, os.path.getsize(attachment), content
                )
            else:
                rprint('[bold][red]File not found[/red][/bold]')

        elif command == ':we':
            self.print_welcome()

        elif command == ':li':
            rprint('\n[#7289DA]' +
                   '=================================================================================\n' +
                   self.rprint_guilds()
                   )

            self.args.channel = input('Channel ID: ')
            try:
                int(self.args.channel)
            except ValueError:
                self.kill_thread = True
                self.main_loop_thread.join()
                sys.exit('Channel ID must be an integer')

            if self.running:
                self.kill_thread = True
                self.main_loop_thread.join()
                self.running = False

            self.args.channel = self.list_id[int(self.args.channel)]
            self.main_loop_thread = threading.Thread(target=self.main_loop)
            self.main_loop_thread.start()
            self.refresh_screen()

        elif command == ':fr':
            rprint('\n[#7289DA]' +
                   '=================================================================================\n' +
                   self.rprint_friends()
                   )

            self.args.channel = input('Channel ID: ')
            try:
                int(self.args.channel)
            except ValueError:
                self.kill_thread = True
                self.main_loop_thread.join()
                sys.exit('Channel ID must be an integer')

            if self.running:
                self.kill_thread = True
                self.main_loop_thread.join()
                self.running = False

            self.args.channel = self.friends[int(self.args.channel) - 1]['id']
            self.main_loop_thread = threading.Thread(target=self.main_loop)
            self.main_loop_thread.start()
            self.refresh_screen()

    def print_welcome(self):
        """ Print the welcome message and the commands list """

        welcome_message = f'Welcome [magenta]{self.get_username_from_id(self.user_id)}[/magenta] !'
        length_welcome_message = len(welcome_message.replace(
            '[magenta]', '').replace('[/magenta]', ''))
        if length_welcome_message < 80:
            welcome_message = '|' + (' ' * ((80 - length_welcome_message) // 2)) + \
                welcome_message + \
                (' ' * ((80 - length_welcome_message) // 2)) + '|'

        rprint('\n[#7289DA]' +
               '=================================================================================\n' +
               '|[#E01E5A]     ▄▄▄▄      ▄▄▄▄▄▄▄▄▄   ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄   [/#E01E5A]|\n' +
               '|[#E01E5A]   ▄█░░░░▌    ▐░░░░░░░░░▌ ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░▌  [/#E01E5A]|\n' +
               '|[#E01E5A]  ▐░░▌▐░░▌   ▐░█░█▀▀▀▀▀█░▌▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀█░▌▐░█▀▀▀▀▀▀▀█░▌▐░█▀▀▀▀▀▀▀█░▌ [/#E01E5A]|\n' +
               '|[#E01E5A]   ▀▀ ▐░░▌   ▐░▌▐░▌    ▐░▌▐░▌          ▐░▌       ▐░▌▐░▌       ▐░▌▐░▌       ▐░▌ [/#E01E5A]|\n' +
               '|[#E01E5A]      ▐░░▌   ▐░▌ ▐░▌   ▐░▌▐░▌          ▐░▌       ▐░▌▐░█▄▄▄▄▄▄▄█░▌▐░▌       ▐░▌ [/#E01E5A]|\n' +
               '|[#E01E5A]      ▐░░▌   ▐░▌  ▐░▌  ▐░▌▐░▌          ▐░▌       ▐░▌▐░░░░░░░░░░░▌▐░▌       ▐░▌ [/#E01E5A]|\n' +
               '|[#E01E5A]      ▐░░▌   ▐░▌   ▐░▌ ▐░▌▐░▌          ▐░▌       ▐░▌▐░█▀▀▀▀█░█▀▀ ▐░▌       ▐░▌ [/#E01E5A]|\n' +
               '|[#E01E5A]      ▐░░▌   ▐░▌    ▐░▌▐░▌▐░▌          ▐░▌       ▐░▌▐░▌     ▐░▌  ▐░▌       ▐░▌ [/#E01E5A]|\n' +
               '|[#E01E5A]  ▄▄▄▄█░░█▄▄▄▐░█▄▄▄▄▄█░█░▌▐░█▄▄▄▄▄▄▄▄▄ ▐░█▄▄▄▄▄▄▄█░▌▐░▌      ▐░▌ ▐░█▄▄▄▄▄▄▄█░▌ [/#E01E5A]|\n' +
               '|[#E01E5A] ▐░░░░░░░░░░░▌▐░░░░░░░░░▌ ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░▌       ▐░▌▐░░░░░░░░░░▌  [/#E01E5A]|\n' +
               '|[#E01E5A]  ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀   ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀         ▀  ▀▀▀▀▀▀▀▀▀▀   [/#E01E5A]|\n' +
               '=================================================================================\n' +
               f'{welcome_message}\n' +
               '=================================================================================\n'
               '| [magenta]Available commands: [/magenta]                                                          |\n' +
               '|   :help - Show this help                                                      |\n' +
               '|   :q - Exit 10cord                                                            |\n' +
               '|   :attach - Attach a file (ex: :attach:/home/user/poop.png:Look, it\'s you!)   |\n' +
               '|   :cr - Clear and Refresh the screen                                          |\n' +
               '|   :li - List Guilds & Channels                                                |\n'
               '|   :fr - List Friends                                                          |\n'
               '|   :we - Print welcome message                                                 |\n'
               '=================================================================================[/#7289DA]'
               )

    def main_loop(self):
        """
        The main_loop function retrieves and prints messages, then continuously checks for new
        messages and prints any differences.
        """

        self.messages = self.get_messages()
        self.print_messages(self.messages)
        self.kill_thread = False
        self.running = True

        started = time.time()
        while not self.kill_thread:
            if time.time() - started >= 3:
                new_messages = self.get_messages()
                diff_messages = self.diff_messages(new_messages, self.messages)
                self.print_messages(diff_messages)
                self.messages = new_messages
                started = time.time()
            else:
                time.sleep(0.1)

    def clean(self):
        """ Clean the tmp folder """

        for file in os.listdir('./tmp'):
            os.remove(f'./tmp/{file}')
        os.rmdir('./tmp')

    def main(self):
        """
        The main function starts a thread for the main loop and then waits for user input to send a
        message.
        """

        self.print_welcome()

        self.running = False
        self.list_id = {}

        def query_data():
            """ Query data from Discord API in a thread """

            self.list_friends()
            self.rprint_friends()
            self.list_guilds()
            self.rprint_guilds()

        def loading_bar(symbol):
            """ Simple loading bar while we fetch the datas from the API

            :param symbol: the current symbol of the loading bar
            :return: the next symbol of the loading bar
            """

            symbols = ['|', '/', '-', '\\']
            return symbols[symbols.index(symbol) + 1] if symbols.index(symbol) < 3 else symbols[0]

        query_data_thread = threading.Thread(target=query_data)
        query_data_thread.start()

        symbol = '|'
        while query_data_thread.is_alive():
            symbol = loading_bar(symbol)
            print(f'Loading... {loading_bar(symbol)}', end='\r')
            time.sleep(0.1)

        for guild in self.guilds:
            for channel in guild['channels']:
                self.list_id[channel['local_id']] = channel['id']

        if not self.args.channel:
            while self.args.channel is None:
                command = input('What should we do : ')
                if command == ':cr' or ':attach' in command:
                    print('Please, select a channel first')
                else:
                    self.internal_command(command)
        else:
            self.main_loop_thread = threading.Thread(target=self.main_loop)
            self.main_loop_thread.start()
            self.refresh_screen()

        commands_list = [':q', ':help', ':cr', ':li', ':fr', ':we']

        while 1:
            try:
                time.sleep(1)
                content = input()
                if content != '' and ':attach' not in content and content not in commands_list:
                    message_sent = self.send_message(content)
                else:
                    self.internal_command(content)

            except KeyboardInterrupt:
                self.kill_thread = True
                self.main_loop_thread.join()
                self.clean()
                sys.exit()


def main():
    """ This main function is used to make an entry point for the program."""

    client = MyClient()
    client.main()


if __name__ == "__main__":
    main()
