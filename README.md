# NotPixelBot By Looters Era

AutoPaint Bot For NotPixel With Added Antiban.

## Requirements

[![Python](https://img.shields.io/badge/python-%3E%3D3.10-3670A0?style=flat&logo=python&logoColor=ffdd54)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-%3E%3D20.18.0-6DA55F?style=flat&logo=node.js&logoColor=white)](https://nodejs.org/)

## Features  

<table>
  <thead>
    <tr>
      <th>Feature</th>
      <th>Supported</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Human Like Paints</td>
      <td>✅</td>
    </tr>
    <tr>
      <td>API change detection</td>
      <td>✅</td>
    </tr>
    <tr>
      <td>Proxy Support</td>
      <td>✅</td>
    </tr>
    <tr>
      <td>Auto-detect new .session and register it in bot</td>
      <td>✅</td>
    </tr>
    <tr>
      <td>Auto-paiting</td>
      <td>✅</td>
    </tr>
    <tr>
      <td>Auto-tasks</td>
      <td>✅</td>
    </tr>
    <tr>
      <td>Auto-claim PX</td>
      <td>✅</td>
    </tr>
    <tr>
      <td>Auto-upgrade boosters</td>
      <td>✅</td>
    </tr>
    <tr>
      <td>Night mode</td>
      <td>✅</td>
    </tr>
    <tr>
      <td>Async working</td>
      <td>✅</td>
    </tr>
  </tbody>
</table>

### 🔍 Human Like Painting

We use **real** task solutions for Human Like Paint instead of random responses, so you don't get banned.

There is still a chance of being banned, but it we did everything possible to prevent it.

### 🎨 Auto-Painting

We don't use random coordinates to paint on the canvas.

Our script automatically paints on the canvas using a template using data received from the websocket connection. It means that you will receive a PX for each painting you make!


## [Settings](https://github.com/asish1346/NotPixelBot/blob/master/.env-example)

<table>
  <thead>
    <tr>
      <th>Settings</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>API_ID / API_HASH</td>
      <td>API credentials for Telegram API</td>
    </tr>
    <tr>
      <td>PLAY_INTRO</td>
      <td>True/False playing intro on script start (DON'T YOU DARE TO TURN THIS OFF)</td>
    </tr>
    <tr>
      <td>INITIAL_START_DELAY_SECONDS</td>
      <td>Delay range in seconds to use for a random delay when starting the session</td>
    </tr>
    <tr>
      <td>ITERATION_SLEEP_MINUTES</td>
      <td>How long the script will wait before starting the next iteration of the script (painting, claiming and e.t.c)</td>
    </tr>
    <tr>
      <td>USE_REF</td>
      <td>True/False the use of a referral to start the bot</td>
    </tr>
    <tr>
      <td>REF_ID</td>
      <td>Referral ID to be used</td>
    </tr>
    <tr>
      <td>SLEEP_AT_NIGHT</td>
      <td>True/False sleep at night</td>
    </tr>
    <tr>
      <td>NIGHT_START_HOURS</td>
      <td>Start hours range of the night</td>
    </tr>
    <tr>
      <td>NIGHT_END_HOURS</td>
      <td>End hours range of the night</td>
    </tr>
    <tr>
      <td>ADDITIONAL_NIGHT_SLEEP_MINUTES</td>
      <td>Additional minutes range to sleep at night</td>
    </tr>
    <tr>
      <td>CLAIM_PX</td>
      <td>True/False auto-claim px</td>
    </tr>
    <tr>
      <td>UPGRADE_BOOSTS</td>
      <td>True/False auto-upgrade boosters</td>
    </tr>
    <tr>
      <td>PAINT_PIXELS</td>
      <td>True/False auto-painting</td>
    </tr>
    <tr>
      <td>COMPLETE_TASKS</td>
      <td>True/False auto-completing tasks</td>
    </tr>
  </tbody>
</table>

## How to start 📚

Before you begin, make sure you have meet the [requirements](#requirements)

## Obtaining API Keys

1. Go to my.telegram.org and log in using your phone number.
2. Select "API development tools" and fill out the form to register a new application.
3. Record the API_ID and API_HASH provided after registering your application in the .env file.

Sometimes when creating a new application, it may display an error. It is still not clear what causes this, but you can try the solutions described on [stackoverflow](https://stackoverflow.com/questions/68965496/my-telegram-org-sends-an-error-when-i-want-to-create-an-api-id-hash-in-api-devel).

## Linux manual installation

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install poetry
poetry install --only main
cp .env-example .env
nano .env  # Specify your API_ID and API_HASH, the rest is taken by default
```

## Windows manual installation

```shell
python -m venv .venv
.venv\Scripts\activate
pip install poetry
poetry install --only main
copy .env-example .env
# Then open .env in any text editor and specify your API_ID and API_HASH, the rest is taken by default
```

### Using start.bat

You can run the script using start.bat script, just execute it by 

```shell
start.bat
```

### Manually

Before running the script, you always need to activate the virtual environment.

```shell
# Linux
source .venv\bin\activate
# Windows
.venv\Scripts\activate
```

To run the script, use `python3 main.py` on Linux or `python main.py` on Windows.

Also, you can use flag `--action` or `-a` to quickly run the script with specified action.

```shell
# Linux
python3 main.py --action [1/2]
# Windows
python main.py --action [1/2]

# Or

# Linux
python3 main.py -a [1/2]
# Windows
python main.py -a [1/2]
```

Where [1/2] is:

    1 - Creates a session
    2 - Run bot

So for example if you want to create a session, you can run this command:

```shell
# Linux
python3 main.py --action 1
# Windows
python main.py --action 1

# Or

# Linux
python3 main.py -a 1
# Windows
python main.py -a 1
```

## Contacts

If you have any questions or suggestions, please feel free to contact us in comments.

[![Looters Era Telegram Channel](https://img.shields.io/badge/Looters%20Era-Join-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/Lootersera_th)
