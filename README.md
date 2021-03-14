# JIRA Issue to Slack

* PyCon JPのJIRAのissueをSlackに通知するプログラム

## 実行環境の構築

* 以下の手順で実行環境が作成できます

```bash
$ git clone https://github.com/pyconjp/jira-issue-report.git
$ cd jira-issue-report
$ python3.8 -m venv env
$ . env/bin/activate
(env) $ pip install -r requirements.txt
(env) $ cp config.ini.sample config.ini
(env) $ vi config.ini
(env) $ ./issue.py
```

* 以下の `config.ini.sample` を `config.ini` にコピーして、各種パスワードやトークンを設定します

```ini
[DEFAULT]
# JIRA username / password
username = JIRA username
password = JIRA password
# Slack API token
token = Slack API token
# debug mode(True or False)
debug = False
```

## 開発環境の構築

* 開発環境を構築する際は `requirements-dev.txt` を使用します。

```bash
$ git clone https://github.com/pyconjp/jira-issue-report.git
$ cd jira-issue-report
$ python3.8 -m venv env
$ . env/bin/activate
(env) $ pip install -r requirements-dev.txt
```

* toxでisort, black, flake8, mypyのチェックが実行できます

```bash
(env) $ tox  # 全部チェックする場合
:
___________________________________ summary ____________________________________
  py38: commands succeeded
  lintcheck: commands succeeded
  mypy: commands succeeded
  congratulations :)
(env) $ tox -elintcheck  # lintだけチェックする場合
:
___________________________________ summary ____________________________________
  lintcheck: commands succeeded
  congratulations :)
(env) $ tox -emypy  # mypyだけチェックする場合
:
___________________________________ summary ____________________________________
  mypy: commands succeeded
  congratulations :)
```

## Sample

* 以下のようなissueレポートがSlackに送信されます

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
