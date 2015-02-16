=====================
 JIRA Issue to Slack
=====================
issue.py post JIRA issue list message to Slack channel.

::

  $ virtualenv -p python3 .venv
  $ . .venv/bin/activate
  (.venv)$ pip install -r requirements.txt
  (.venv)$ cp config.ini.sample config.ini
  (.venv)$ vi config.ini.sample
  (.venv)$ ./issue.py

config.ini.sample::

  [DEFAULT]
  username = JIRA username
  password = JIRA password
  webhook_url = Slack webhook URL

