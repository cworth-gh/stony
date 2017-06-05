###
# Imports
###

from __future__ import unicode_literals
from slackclient import SlackClient
from threading import Timer

import yaml

###
# Global Variables
###

# The Slack API client.
config = yaml.load(file('stony.conf', 'r'))
slack_client = SlackClient(config['SLACK_TOKEN'])

# A list of outputs; append to this list to send a message.
outputs = []

# A list of timers.
timers = []

# A map of stored inputs.
inputs = {}

# A map of scores.
scores = {}

###
# Constants
###

COMMAND_CLEAR = 'CLEAR'
COMMAND_INPUT = 'INPUT'
COMMAND_REVEAL = 'REVEAL'
COMMAND_SCORE = 'SCORE'
COMMAND_SCORES = 'SCORES'
COMMAND_START = 'START'
COMMAND_STOP = 'STOP'

###
# Bot Utility Functions
###

def send_message(message, channel):
    outputs.append([channel, '>>>' + message])

def get_im_id_for_user_id(user_id):
    api_call = slack_client.api_call('im.open', user=user_id)
    if api_call.get('ok'):
        return api_call.get('channel').get('id')
    return ''

def get_username_for_user_id(user_id):
    api_call = slack_client.api_call('users.info', user=user_id)
    if api_call.get('ok'):
        return api_call.get('user').get('name')
    return ''

def is_int(str):
    try: 
        int(str)
        return True
    except ValueError:
        return False

###
# Game Functions
###

def reveal_inputs(channel):
    global inputs
    if len(inputs) == 0:
        send_message('Nothing to reveal!', channel)
        return

    message = ''
    for user_id, input in inputs.iteritems():
        message += '*' + user_id + '*: ' + input + '\n'
    send_message(message, channel)
    inputs = {}

def show_scores(channel):
    message = '*Scores:*\n'
    for user_id, score in scores.iteritems():
        message += '*' + user_id + '*: ' + str(score) + '\n'
    send_message(message, channel)

def clear_scores(channel):
    global scores
    scores = {}
    message = 'Scores cleared.'
    send_message(message, channel)

def timer_end(channel):
    send_message('Time\'s up!', channel)
    reveal_inputs(channel)

def start_timer(start_seconds, remaining_seconds, channel):
    global timers
    message = ''
    if remaining_seconds > 60:
        message = str(remaining_seconds / 60) + ' minutes remaining.'
    else:
        message = str(remaining_seconds) + ' seconds remaining.'
    timer = Timer(start_seconds - remaining_seconds, send_message, [message, channel])
    timer.start()
    timers.append(timer)

def start_timers(seconds, channel):
    global timers

    # Announce!
    send_message(str(start_seconds) + ' seconds starts now!', channel)

    # Store the starting length.
    start_seconds = seconds 

    # Drop down to a multiple of 60 seconds.
    if seconds > 60:
        seconds -= seconds % 60

    # Set timers for every minute above 60 seconds remaining.
    while seconds > 60:
        minutes = seconds / 60
        start_timer(start_seconds, seconds, channel)
        seconds -= 60

    # Set timers for one minute or less.
    short_times = [60, 30, 15]
    for short_time in short_times:
        if seconds >= short_time:
            start_timer(start_seconds, short_time, channel)

    # Set the main timer.
    timer = Timer(start_seconds, timer_end, [channel])
    timer.start()
    timers.append(timer)

def clear_timers(channel):
    global timers
    for timer in timers:
        timer.cancel()
    timers = []
    send_message('Timers cleared.', channel)

###
# Bot Main Functions
###

# This function is called whenever a message is received.
def process_message(data):
    global inputs

    # Get the text and the channel.
    message_text = data['text']
    channel = data['channel']
    username = get_username_for_user_id(data['user'])

    # If it's a REVEAL message, spill the beans.
    if message_text == COMMAND_REVEAL:
        reveal_inputs(channel)
        return

    # If it's a SCORES message, show the scores.
    if message_text == COMMAND_SCORES:
        show_scores(channel)
        return

    # If it's a CLEAR message, clear the scores.
    if message_text == COMMAND_CLEAR:
        clear_scores(channel)
        return

    # If it's a SCORE message, add to the score.
    if message_text.startswith(COMMAND_SCORE + ' '):
        # Chop off the SCORE command token.
        message_text = message_text.split(' ', 1)[1]

        # Send an error message if the score isn't an integer.
        if not is_int(message_text):
            send_message('That\'s not an integer.', channel)
            return
 
        # Add the score to the player's score in the map.
        if username not in scores:
            scores[username] = 0
        scores[username] += int(message_text)
        message = '*' + username + '*\'s score is now ' + str(scores[username]) + '.'
        send_message(message, channel)
        return

    # If it's an INPUT message, accept the input.
    if message_text.startswith(COMMAND_INPUT + ' '):
        # Chop off the INPUT command token.
        message_text = message_text.split(' ', 1)[1]

        # Store the pairing in the map.
        inputs[username] = message_text
        send_message('Got it!', channel)
        return

    # If it's a START message, begin the timer.
    if message_text.startswith(COMMAND_START + ' '):
        # Chop off the START command token.
        message_text = message_text.split(' ', 1)[1]

        # Send an error message if the timer length isn't an integer.
        if not is_int(message_text):
            send_message('That\'s not an integer.', channel)
            return

        # Start the timer.
        start_timers(int(message_text), channel)
        return

    # If it's a STOP message, clear the timers.
    if message_text == COMMAND_STOP:
        clear_timers(channel)
        return
