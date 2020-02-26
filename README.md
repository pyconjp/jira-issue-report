# JIRA Issue to Slack

issue.py post JIRA issue list message to Slack channel.

```
$ git clone https://github.com/pyconjp/jira-issue-report.git
$ cd jira-issue-report
$ python3.7 -m venv env
$ . env/bin/activate
(env)$ pip install -r requirements.txt
(env)$ cp config.ini.sample config.ini
(env)$ vi config.ini
(env)$ ./issue.py
```

config.ini.sample

```
[DEFAULT]
# JIRA username / password
username = JIRA username
password = JIRA password
# Slack API token
token = Slack API token
# debug mode(True or False)
debug = False
```

## Sample

Sample of issue report

```
[13:34] 
​*一般社団法人*​ の「もうすぐ期限切れチケット」ハ ​*3件*​ デス┗┃￣□￣；┃┓ 
- 2016-02-03 ISSHA-155: 2016の会場を予約する(@takanory)
- 2016-02-05 ISSHA-214: 2015年の総括を報告(@terada)
- 2016-02-05 ISSHA-198: 2015年度活動の総括(@terada)

[13:34] 
チケットノ状況デス
:sunny: ​*メディア*​ (#t-media) 期限切れ ​*0*​ もうすぐ期限切れ ​*2*​
:sunny: ​*会場*​ (#t-venue) 期限切れ ​*0*​ もうすぐ期限切れ ​*0*​
:sunny: ​*プログラム*​ (#t-program) 期限切れ ​*2*​ もうすぐ期限切れ ​*0*​
:sunny: ​*全体、環境、その他*​ (#2015) 期限切れ ​*0*​ もうすぐ期限切れ ​*0*​
:sunny: ​*事務局*​ (#t-jimukyoku) 期限切れ ​*2*​ もうすぐ期限切れ ​*0*​
```
