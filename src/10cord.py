import requests
import fake_useragent
from rich import print as rprint
import os
import json
import time
import argparse
import threading


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

    return parser.parse_args()


class MyClient():
    def __init__(self) -> None:
        self.args = parse_args()
        self.url = "https://discord.com/api/v9"
        if os.path.exists('token.json'):
            with open('token.json', 'r', encoding='utf-8') as f:
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

    def login(self):
        """
        The `login` function sends a POST request to a specified URL with login credentials, and if
        successful, saves the user ID, token, and timestamp to a JSON file.
        """

        data = {
            "login": self.args.email,
            "password": self.args.password,
            "undelete": False,
            "login_source": None,
            "gift_code_sku_id": None
        }

        response = requests.post(
            f'{self.url}/auth/login',
            json=data,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(f'Login failed : {response.status_code} {response.text}')

        self.user_id = response.json()['user_id']
        self.token = response.json()['token']
        self.timestamp = str(time.time())

        with open('token.json', 'w', encoding='utf-8') as f:
            json.dump({'user_id': self.user_id, 'token': self.token,
                      'timestamp': self.timestamp}, f, indent=4)

    def get_messages(self):
        """
        The function `get_messages` retrieves the latest 100 messages from a specified channel using the
        Discord server.
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
            raise Exception(f'Get messages failed : {response.status_code} {response.text}')

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
                user_id = content.split('<@')[1].split('>')[0]
                username = self.get_username_from_id(user_id)
                content = content.replace(f'<@{user_id}>', f'[bold]@{username}[/bold]')

            rprint(f'[bold][blue][{date}][/blue] [magenta]{username}[/magenta][/bold] : {content}')

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

    def send_message(self, content):
        """
        The `send_message` function sends a message to a specified channel using the Discord API.

        :param content: The `content` parameter is the message content that you want to send.
        :return: the JSON response from the API call.
        """

        data = {
            'content': content
        }

        response = requests.post(
            f'{self.url}/channels/{self.args.channel}/messages',
            headers=self.headers,
            json=data,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(f'Send message failed : {response.status_code} {response.text}')

        return response.json()

    def get_username_from_id(self, user_id):
        """
        The function `get_username_from_id` retrieves the username associated with a given user ID
        from the Discord API.

        :param user_id: The `user_id` parameter is the unique identifier of a user.
        :return: the username of the user with the given user_id if the response status code is 200.
        Otherwise, it returns the user_id itself.
        """

        response = requests.get(
            f'{self.url}/users/{user_id}',
            headers=self.headers,
            timeout=5
        )

        if response.status_code != 200:
            return user_id

        return response.json()['username']

    def main_loop(self):
        """
        The main_loop function retrieves and prints messages, then continuously checks for new
        messages and prints any differences.
        """

        messages = self.get_messages()
        self.print_messages(messages)

        while 1:
            time.sleep(3)
            new_messages = self.get_messages()
            diff_messages = self.diff_messages(new_messages, messages)
            self.print_messages(diff_messages)
            messages = new_messages

    def main(self):
        """
        The main function starts a thread for the main loop and then waits for user input to send a
        message.
        """

        main_loop_thread = threading.Thread(target=self.main_loop)
        main_loop_thread.start()

        while 1:
            time.sleep(1)
            content = input()
            if content:
                message_sent = self.send_message(content)


if __name__ == "__main__":
    client = MyClient()
    client.main()
