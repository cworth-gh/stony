###
# Imports
###

from __future__ import unicode_literals
from slackclient import SlackClient

import yaml


###
# Global Variables
###

# A list of outputs; append to this list to send a message.
outputs = []

# The Slack API client.
config = yaml.load(file('stony.conf', 'r'))
slack_client = SlackClient(config['SLACK_TOKEN'])


###
# State Variables
###

# The player and round counts.
number_of_rounds = 7
minimum_number_of_players = number_of_rounds + 2

# The channel in which the game is occurring.
# If this is non-empty, the game is in progress.
game_channel = ''

# The list of players.
player_list = []

# The current round.
current_round = -1

# The trivia answers.
answer_list = []

# The questions, so far.
question_list = []

# The number of players who have submitted their word for this round.
words_received = 0

# The current question to present in the trivia round.
presentation_index = -2

# This is True is a question is currently presented.
question_is_presented = False


###
# Classes
###

class Player:
    id = ''
    name = ''
    im_id = ''
    index = -1

    def __init__(self, player_name):
        self.id = get_id_for_username(player_name)
        self.name = player_name
        self.im_id = get_im_id_for_user_id(self.id)


###
# Bot Utility Functions
###

def send_message(message, channel):
    outputs.append([channel, '>>>' + message])

def get_id_for_username(username):
    api_call = slack_client.api_call('users.list')
    if api_call.get('ok'):
        users = api_call.get('members')
        for user in users:
            if 'name' in user and user.get('name') == username:
                return user.get('id')
    return ''

def get_im_id_for_user_id(user_id):
    api_call = slack_client.api_call('im.open', user=user_id)
    if api_call.get('ok'):
        return api_call.get('channel').get('id')
    return ''

def get_channel_name_for_id(channel_id):
    api_call = slack_client.api_call('channels.info', channel=channel_id)
    if api_call.get('ok'):
        return api_call.get('channel').get('name')
    return ''


###
# Game Functions
###

def update_number_of_rounds(new_number_of_rounds, channel):
    global number_of_rounds, minimum_number_of_players
    number_of_rounds = new_number_of_rounds
    minimum_number_of_players = number_of_rounds + 2
    message = 'Number of rounds updated to *' + str(new_number_of_rounds) + '*.'
    send_message(message, channel)

def add_player(player_name, channel):
    # Check if the player has already been added.
    for player in player_list:
        if player.name == player_name:
            message = '*' + player_name + '* is already signed up to play.'
            send_message(message, channel)
            return

    # No such player yet, so go ahead.
    player = Player(player_name)
    if player.id == '':
        handle_invalid_player_name(player_name, channel)
        return
    player_list.append(player)
    message = '*' + player_name + '* is now signed up to play.'
    send_message(message, channel)

def remove_player(player_name, channel):
    global player_list
    player_removed = False
    message = ''
    new_player_list = []
    for player in player_list:
        if player.name == player_name:
            player_removed = True
            message = '*' + player_name + '* has been removed.'
        else:
            new_player_list.append(player)
    player_list = new_player_list
    if not player_removed:
        message = '*' + player_name + '* wasn\'t signed up to play.'
    send_message(message, channel)

def list_players(channel):
    if len(player_list) == 0:
        message = 'No registered players.'
    else:
        message = '*Registered players:* '
        for player in player_list:
            message += player.name + ', '
        message = message[:-2]
    send_message(message, channel)

def prepare_players():
    for i in xrange(len(player_list)):
        player_list[i].index = i
        answer_list.append('')
        question_list.append([])

def start_game(channel):
    global game_channel
    if len(player_list) < minimum_number_of_players:
        message = 'Cannot start game; we have '
        message += '*' + str(len(player_list)) + '/' + str(minimum_number_of_players) + '* players.'
        send_message(message, channel)
        return

    prepare_players()
    game_channel = channel
    gather_answers()

def gather_answers():
    global current_round, words_received
    current_round = 0
    words_received = 0
    message = 'Please enter the answer to your trivia question.'
    for player in player_list:
        send_message(message, player.im_id)

def start_next_round():
    global current_round, words_received
    current_round += 1
    words_received = 0
    for player in player_list:
        answer_index = (player.index + current_round) % len(player_list)
        message = 'The answer to this trivia question is *\'' + answer_list[answer_index] + '\'*.\n'
        if current_round == 1:
            message += 'Please enter the *first three words* of this trivia question.'
        elif current_round < number_of_rounds:
            message += 'The previous word in this question is *\'' + question_list[answer_index][(current_round - 1) * 2] + '\'*.\n'
            message += 'Please enter the *next two words* of this trivia question.\n'
            message += '(These are the *' + str(current_round * 2) + 'th and ' + str((current_round * 2) + 1) + 'th* words out of *' + str(number_of_rounds * 2) + '*.)'
        else:
            message += 'The previous word in this question is *\'' + question_list[answer_index][(current_round - 1) * 2] + '\'*.\n'
            message += 'Please enter the *' + str(number_of_rounds * 2) + 'th and final word* of this trivia question.'
        send_message(message, player.im_id)

def add_question_words(words, player):
    global words_received
    # Validate based on the current round.
    expected_word_count = 3 if current_round == 1 else 1 if current_round == number_of_rounds else 2
    if len(words) == expected_word_count:
        question_index = (player.index + current_round) % len(player_list)
        question_list[question_index].extend(words)
        words_received += 1
        message = 'Thanks!  Please wait for the ' + ('next' if current_round < number_of_rounds else 'trivia') + ' round.'
    else:
        message = 'Please enter exactly '
        message += 'three words.' if expected_word_count == 3 else 'one word.' if expected_word_count == 1 else 'two words.'
    send_message(message, player.im_id)

def check_for_next_round():
    if words_received == len(player_list):
        if current_round < number_of_rounds:
            start_next_round()
        else:
            start_trivia_round()

def start_trivia_round():
    global presentation_index
    presentation_index = -1
    message = '*Time for the trivia round!*  Type `xfruit go` to present the first question.'
    send_message(message, game_channel)

    game_channel_name = get_channel_name_for_id(game_channel)
    message = 'All done!  Please head to *#' + game_channel_name + '* for the trivia round.'
    for player in player_list:
        send_message(message, player.im_id)

def continue_trivia_round():
    global question_is_presented, presentation_index
    game_is_over = False
    if not question_is_presented:
        question_is_presented = True
        presentation_index += 1
        message = 'This question is for *' + player_list[presentation_index].name + '*:\n'
        message += '    ' + ' '.join(question_list[(presentation_index - 1) % len(player_list)])
        if not message.endswith('?'):
            message += '?'
    else:
        question_is_presented = False
        message = 'The answer to the previous question was *\'' + answer_list[(presentation_index - 1) % len(player_list)] + '\'*.'
        if presentation_index == len(player_list) - 1:
            game_is_over = True
        else:
            message += '\nType `xfruit go` to move on to the next question.'

    send_message(message, game_channel)

    if game_is_over:
        end_game()

def end_game():
    global current_round, words_received, presentation_index
    global player_list, question_list, answer_list, game_channel
    current_round = -1
    words_received = 0
    presentation_index = -2
    player_list = []
    question_list = []
    answer_list = []
    message = 'That\'s it for this game of Exquisite Fruit.  Thanks for playing!'
    send_message(message, game_channel)
    game_channel = ''


###
# Error Handling Functions
###

def handle_missing_params(command, channel):
    message = 'I need more parameters for the command *\'' + command + '\'*.'
    send_message(message, channel)

def handle_invalid_player_name(player_name, channel):
    message = 'I can\'t find the user *\'' + player_name + '\'*.'
    send_message(message, channel)


###
# Bot Main Functions
###

# TODO: Create maps from IM id to user and from user to player index.
# Not a huge deal right now, since we'll roughly be dealing with eight players.

def process_message(data):
    global words_received
    message_text = data['text']
    message_tokens = message_text.split()
    channel = data['channel']

    # We check whether the game has started by checking if there's a game channel.
    # If the game hasn't started, the only processed commands are:
    #   * xfruit player [username]
    #   * xfruit unplayer [username]
    #   * xfruit start

    if game_channel == '':
        if message_tokens[0] != 'xfruit':
            return
        command = message_tokens[1]
        if command == 'rounds':
            if len(message_tokens) < 3:
                handle_missing_params(command, channel)
            else:
                update_number_of_rounds(int(message_tokens[2]), channel)
        elif command == 'player':
            if len(message_tokens) < 3:
                handle_missing_params(command, channel)
            else:
                add_player(message_tokens[2], channel)
        elif command == 'unplayer':
            if len(message_tokens) < 3:
                handle_missing_params(command, channel)
            else:
                remove_player(message_tokens[2], channel)
        elif command == 'players':
            list_players(channel)
        elif command == 'start':
            start_game(channel)
        else:
            message = 'Only `xfruit player [player_name]` and `xfruit start` '
            message += 'are valid commands when a game is not in progress.'
        return

    # A game is in progress.
    # If we're in the trivia round (i.e. `presentation_index > -2`), we check
    # for the command `xfruit go`.
    if presentation_index > -2:
        if message_text == 'xfruit go':
            continue_trivia_round()
        return

    # We're not in the trivia round, so we're only accepting question words
    # in private messages.  We need to know which player we're dealing with,
    # so we can appropriately handle the message.
    message_sender_id = data['user']
    for player in player_list:
        if player.id == message_sender_id:
            active_player = player

    # If this isn't in the sender's IM channel, ignore it.
    if channel != active_player.im_id:
        return

    if answer_list[active_player.index] == '':
        # The player is giving us their answer.
        answer_list[active_player.index] = message_text
        words_received += 1
        message = 'Thanks!  Please wait for the next round.'
        send_message(message, active_player.im_id)
    else:
        # The player is adding to the question.
        question_index = (active_player.index + current_round) % len(player_list)
        if len(question_list[question_index]) > (current_round * 2) - 1:
            # We already have this player's input for the round!
            message = 'Please wait for the ' + ('next' if current_round < number_of_rounds else 'trivia') + ' round.'
            send_message(message, active_player.im_id)
            return

        # Accept the given words.
        add_question_words(message_tokens, active_player)

    # Check for round advancement.
    check_for_next_round()
