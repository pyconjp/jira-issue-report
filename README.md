# JIRA Issue to Slack

issue.py post JIRA issue list message to Slack channel.

```
$ virtualenv -p python3 env
$ . env/bin/activate
(env)$ pip install -r requirements.txt
(env)$ cp config.ini.sample config.ini
(env)$ vi config.ini
(env)$ ./issue.py
```

config.ini.sample

```
[DEFAULT]
[DEFAULT]
# JIRA username / password
username = JIRA username
password = JIRA password
# Slack webhook
webhook_url = Slack webhook URL
# debug mode(True or False)
debug = False
```
