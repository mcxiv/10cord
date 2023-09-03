import requests
import fake_useragent
from rich import print as rprint
import os
import json
import time
import argparse
import threading


def parse_args():
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
        self.url = "https://discord.com/api/v9"
        if os.path.exists('token.json'):
            with open('token.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.user_id = data['user_id']
                self.token = data['token']
        else:
            self.login()

        self.args = parse_args()

    def login(self):
        headers = {
            'User-Agent': fake_useragent.UserAgent().random
        }

        data = {
            "login": self.args.email,
            "password": self.args.password,
            "undelete": False,
            "login_source": None,
            "gift_code_sku_id": None
        }

        response = requests.post(
            f'{self.url}/auth/login',
            headers=headers,
            json=data,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(f'Login failed : {response.status_code} {response.text}')

        self.user_id = response.json()['user_id']
        self.token = response.json()['token']

        with open('token.json', 'w', encoding='utf-8') as f:
            json.dump({'user_id': self.user_id, 'token': self.token}, f, indent=4)

    def get_messages(self):
        headers = {
            'Authorization': self.token,
        }

        params = {
            'limit': '100',
        }

        response = requests.get(
            f'https://discord.com/api/v9/channels/{self.args.channel}/messages',
            params=params,
            headers=headers,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(f'Get messages failed : {response.status_code} {response.text}')

        messages = response.json()
        messages.reverse()

        return messages

    def print_messages(self, messages):
        for message in messages:
            date = message['timestamp'].replace('T', ' - ').split('.')[0]
            username = message['author']['username']
            content = message['content']
            if '<@' in content:
                user_id = content.split('<@')[1].split('>')[0]
                username = self.get_username_from_id(user_id)
                content = content.replace(f'<@{user_id}>', f'[bold]@{username}[/bold]')

            rprint(f'[bold][blue][{date}][/blue] [magenta]{username}[/magenta][/bold] : {content}')

    def diff_messages(self, messages1, messages2):
        new_messages = []
        for message in messages1:
            if message not in messages2:
                new_messages.append(message)

        return new_messages

    def send_message(self, content):
        headers = {
            'User-Agent': fake_useragent.UserAgent().random,
            'Authorization': self.token,
        }

        data = {
            'content': content
        }

        response = requests.post(
            f'https://discord.com/api/v9/channels/{self.args.channel}/messages',
            headers=headers,
            json=data,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(f'Send message failed : {response.status_code} {response.text}')

        return response.json()

    def get_username_from_id(self, user_id):
        headers = {
            'User-Agent': fake_useragent.UserAgent().random,
            'Authorization': self.token,
        }

        response = requests.get(
            f'https://discord.com/api/v9/users/{user_id}',
            headers=headers,
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(f'Get username failed : {response.status_code} {response.text}')

        return response.json()['username']

    def main_loop(self):
        messages = self.get_messages()
        self.print_messages(messages)

        while 1:
            time.sleep(3)
            new_messages = self.get_messages()
            diff_messages = self.diff_messages(new_messages, messages)
            self.print_messages(diff_messages)
            messages = new_messages

    def main(self):
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
