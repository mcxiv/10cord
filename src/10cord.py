import requests
import fake_useragent
from rich import print as rprint
import os
import json
import time
import argparse
import threading
import sys
import subprocess as sp


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
        'channel',
        help='Channel ID to get messages from',
    )
    parser.add_argument(
        '-a', '--attach',
        help='If true, displays attachments (Requires chafa)',
        default=False
    )

    return parser.parse_args()


class MyClient():
    def __init__(self) -> None:
        self.args = parse_args()
        self.url = 'https://discord.com/api/v9'

        if not os.path.exists('tmp'):
            os.mkdir('tmp')

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
            'Authorization': self.token,
        }

        self.ids = {}
        self.attachments = []

    def login(self):
        """
        The `login` function sends a POST request to a specified URL with login credentials, and if
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
        The function `get_messages` retrieves the latest 100 messages from a specified channel using the
        Discord server.

        :return: a list of messages.
        """

        params = {
            'limit': '50',
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

    def print_messages(self, messages):
        """
        The function "print_messages" takes in a list of messages and prints them.

        :param messages: The "messages" parameter is a list of messages that you want to print
        """

        for message in messages:
            date = message['timestamp'].replace('T', ' - ').split('.')[0]
            username = message['author']['username']
            content = message['content']
            if '<@' in content and '<@&' not in content:
                # TODO: rework this part to avoid request as mentions is located
                # in the message requests
                user_id = content.split('<@')[1].split('>')[0]
                if user_id not in self.ids:
                    self.ids[user_id] = self.get_username_from_id(user_id)
                username_in_content = self.ids[user_id]
                content = content.replace(
                    f'<@{user_id}>', f'[bold]@{username_in_content}[/bold]')

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

            rprint(
                f'[bold][blue][{date}][/blue] [magenta]{username}[/magenta][/bold] : {content}')

            if message['attachments'] != [] and self.args.attach:
                if os.name == 'posix' and 'Chafa version' in sp.getoutput('chafa --version'):
                    os.system(
                        f'chafa ./tmp/{message["attachments"][0]["filename"]} --size=50x50 --animate=off'
                    )

    def diff_messages(self, messages1, messages2):
        """
        The function `diff_messages` takes two lists of messages and returns a new list containing
        messages that are in the first list but not in the second list.

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
        The `send_message` function sends a message to a specified channel using the Discord API.

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
        The function `get_username_from_id` retrieves the username associated with a given user ID
        from the Discord API.

        :param user_id: Unique identifier of a user.

        :return: the username of the user with the given user_id if the response status code is 200.
        Otherwise, it returns the user_id itself.
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
        This function requests an upload link for a file to a specified channel using the Discord API.

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
        :param content: The `content` parameter is the message content that you want to send.

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
                   '=============================='
                   '[/#7289DA]'
                   )
            rprint()

        elif command == ':q':
            self.kill_thread = True
            self.main_loop_thread.join()
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

    def print_welcome(self):
        """ Print the welcome message and the commands list """

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
               '| Available commands:                                                           |\n' +
               '|   :help - Show this help                                                      |\n' +
               '|   :q - Exit 10cord                                                            |\n' +
               '|   :attach - Attach a file (ex: :attach:/home/user/poop.png:Look, it\'s you!)   |\n' +
               '|   :cr - Clear and Refresh the screen                                          |\n' +
               '=================================================================================\n'
               )

    def main_loop(self):
        """
        The main_loop function retrieves and prints messages, then continuously checks for new
        messages and prints any differences.
        """

        self.messages = self.get_messages()
        self.print_messages(self.messages)
        self.kill_thread = False

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

    def list_guilds(self):
        response = requests.get(
            f'{self.url}/users/@me/guilds',
            headers=self.headers,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(
                f'Get guilds failed : {response.status_code} {response.text}')
        
        self.guilds = response.json()
        # TODO: 
        # - dynamic rprint guilds in welcome message (diff color for owned guilds)
        # - prompt to choose guild
        # - add guilds to internal commands
        # - remove channel args. in command

    def main(self):
        """
        The main function starts a thread for the main loop and then waits for user input to send a
        message.
        """

        self.print_welcome()
        self.main_loop_thread = threading.Thread(target=self.main_loop)
        self.main_loop_thread.start()
        commands_list = [':q', ':help', ':cr']

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
                sys.exit()


if __name__ == "__main__":
    client = MyClient()
    client.main()
