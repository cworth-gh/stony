This plugin handles scoring and private answer submission and revealing.

### How It Works

#### Scoring

* `SCORE [score]`: Add _score_ to your score.
* `SCORES`: Show all scores.
* `CLEAR`: Clear scores.

#### Inputs and Revealing

* `INPUT [answer]`: Set your answer to _answer_.
* `REVEAL`: Show all submitted answers.

#### Timing

* `START [seconds]`: Start a timer for _seconds_ seconds.  It will send reminders with N minutes remaining, along with 30 and 15 seconds.  When time runs out, `REVEAL` will be called automatically.
* `STOP`: Stops all timers.

### To-Do

* Allow the specification of a game leader, who is the only person who can `REVEAL`.
