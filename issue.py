#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
import json

from jira import JIRA
import requests

# 期限切れの issue を取得する QUERY
EXPIRED_QUERY = '''project = HTJ AND status in (Open, "In Progress", Reopened)
 AND due <= "0" ORDER BY due ASC, component ASC'''

# 一週間後に期限切れの issue を取得する QUERY
WEEK_QUERY = '''project = HTJ AND status in (Open, "In Progress", Reopened)
 AND due > "0" AND due <= 7d ORDER BY due ASC, component ASC'''

# JIRAとSlackで id が違う人の対応表
JIRA_SLACK = {
    'koedoyoshida': 'yoshida',
    'checkpoint': 'sekine',
    'Surgo': 'surgo',
    'uni-q': 'uniq.hasizume',
    'ryok.p': 'ryok',
    'urasin2012': 'urasin',
    'yoshicide': 'yoshi',
    'satisfaction': 'ryomanzoku',
    'yamaguchi-kat': 'katsushiyamaguchi',
    'Toshihiro_nakatsuka': 'toshihironakatsuka',
    'y0k0yama.syh': 'syh.yokoyama',
    'redfigure': 'a.osanai',
    'mrasu': 'hiroakisuginaka',
    'fujiihideaki': 'foohee',
    'kohei.itou': 'kohei',
    'kokusyou.ri': 'djghost',
    'tetsuyahasegawa': 'hasegawa',
    'fix7211': 'sotoshigoto',
}


def issue_to_dict(issue):
    """
    issue から必要な値を取り出して、いい感じの辞書にして返す
    """
    # URL に変な文字列が付いているので削除する
    url, none_ = issue.permalink().split(' - ')
    issue_dict = {
        'key': issue.raw['key'],
        'url': url,
        'summary': issue.raw['fields']['summary'],
        'created': issue.raw['fields']['created'],
        'updated': issue.raw['fields']['updated'],
        'duedate': issue.raw['fields']['duedate'],
        'assignee': issue.raw['fields']['assignee']['displayName'],
        'name': issue.raw['fields']['assignee']['name'],
        'email': issue.raw['fields']['assignee']['emailAddress'],
        'priority': issue.raw['fields']['priority']['name'],
        'status': issue.raw['fields']['status']['name'],
        }

    # JIRA の id を Slack の id に変換する
    name = issue_dict['name']
    issue_dict['slack'] = JIRA_SLACK.get(name, name)

    components = []
    for component in issue.raw['fields']['components']:
        components.append(component['name'])
    issue_dict['components'] = components
    issue_dict['component'] = u", ".join(issue_dict['components'])

    return issue_dict


def formatted_issue(issue_dict):
    """
    1件のissueを文字列にして返す
    """
    issue_text = u"- {duedate} <{url}|{key}>: {summary}(@{slack})"
    return issue_text.format(**issue_dict)


def get_issues(username, password):
    """
    JIRAから期限切れ、もうすぐ期限切れのissueの
    """
    # JIRA に接続
    options = {
        'server': 'https://pyconjp.atlassian.net'
        }
    jira = JIRA(options=options, basic_auth=(username, password))
    # 期限切れ
    expired = []
    for issue in jira.search_issues(EXPIRED_QUERY):
        expired.append(issue_to_dict(issue))

    # もうすぐ期限切れ
    soon = []
    for issue in jira.search_issues(WEEK_QUERY):
        soon.append(issue_to_dict(issue))
    return expired, soon


def send_issue_message(title, issues, webhook_url):
    """
    チケットの一覧を Slack に送信する
    """
    # 通知用のテキストを生成
    text = '{}({}件)\n'.format(title, len(issues))
    for issue in issues:
        text += formatted_issue(issue) + '\n'

    # メッセージを Slack に送信
    payload = {
        'channel': 'slack-test',
        'username': 'PyCon JP issue bot',
        'icon_emoji': ':pyconjp:',
        'fallback': title,
        'text': text,
        'link_names': 1,
        }
    r = requests.post(webhook_url, data=json.dumps(payload))
    return r


def main(username, password, webhook_url):
    """
    期限切れ、もうすぐ期限切れのチケットの一覧を取得してSlackで通知する
    """

    # 期限切れ(expired)、もうすぐ期限切れ(soon)のチケット一覧を取得
    expired, soon = get_issues(username, password)

    send_issue_message('期限切れチケット', expired, webhook_url)
    send_issue_message('もうすぐ期限切れチケット', soon, webhook_url)

if __name__ == '__main__':
    # config.ini からパラメーターを取得
    config = configparser.ConfigParser()
    config.read('config.ini')
    username = config['DEFAULT']['username']
    password = config['DEFAULT']['password']
    webhook_url = config['DEFAULT']['webhook_url']

    main(username, password, webhook_url)
