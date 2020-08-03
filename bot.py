import os
import random
import re
from functools import partial
from typing import NamedTuple, List

import toml
from matrix_client.client import MatrixClient
from matrix_client.errors import MatrixRequestError
from matrix_client.room import Room
from matrix_client.user import User


class Config(NamedTuple):
    server: str
    username: str
    password: str
    groups: List[str]


def load_config() -> Config:
    with open('config.toml') as f:
        d = toml.load(f)
    return Config(**d)

def on_message(matrix: MatrixClient, room: Room, event: dict):
    sender = event['sender']
    content = event['content']
    message_type = content['msgtype']
    if message_type != 'm.text':
        return
    text = content['body']
    res = re.search(r"^\.r(\d+)?d(\d+)?(?:\s+(.+?))?$", text)
    if not res:
        return
    m, n, msg = res.groups()
    m = m and int(m) or 1
    n = n and int(n) or 100
    msg = msg or ''
    if m > 20:
        room.send_text("骰子 太 多 了")
        return
    if n == 0:
        room.send_text("? ? ? ? ?")
        return
    dices = [
        random.randint(1, n)
        for _ in range(m)
    ]
    user: User = matrix.get_user(sender)
    if m > 1:
        dice_message = "+".join(map(str, dices)) + f"={sum(dices)}"
    else:
        dice_message = str(dices[0])
    message = f"{user.get_display_name()} 投掷 R{m}D{n} {msg} 结果为 {dice_message}"
    room.send_text(message)

def init_client(config: Config) -> MatrixClient:
    url = f"https://{config.server}"
    if os.path.exists('token.txt'):
        with open('token.txt') as f:
            token = f.read()
        matrix = MatrixClient(url, user_id=f"@{config.username}:{config.server}", token=token)
    else:
        matrix = MatrixClient(url)
        try:
            token = matrix.login(config.username, config.password)
        except MatrixRequestError:
            token = matrix.register_with_password(config.username, config.password)
        with open('token.txt', 'w') as f:
            f.write(token)

    for name in config.groups:
        room_id = f"#{name}:{config.server}"
        room = matrix.join_room(room_id)
        room.add_listener(partial(on_message, matrix), 'm.room.message')
    matrix.listen_forever()


def main():
    config = load_config()
    matrix = init_client(config)


if __name__ == '__main__':
    main()
