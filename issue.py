#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
import json
import random

from jira import JIRA
import requests

# issue を取得する QUERY
QUERY = '''project = {project} AND status in (Open, "In Progress", Reopened)
 AND {due} ORDER BY due ASC, component ASC'''

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
    'Ds110': 'ds110',
}

# JIRA サーバー
SERVER = 'https://pyconjp.atlassian.net'

# ロボット顔文字
FACES = ('┗┫￣皿￣┣┛', '┗┃￣□￣；┃┓ ',
         '┏┫￣皿￣┣┛', '┗┃・ ■ ・┃┛',
         '┗┫＝皿[＋]┣┛')

def issue_to_dict(issue):
    """
    issue から必要な値を取り出して、いい感じの辞書にして返す
    """
    # 担当者が存在しない場合はnameをNoneにする
    assignee = issue.raw['fields']['assignee']
    if assignee is None:
        name = None
    else:
        name = assignee['name']

    issue_dict = {
        'key': issue.raw['key'],
        'url': issue.permalink(),
        'summary': issue.raw['fields']['summary'],
        'created': issue.raw['fields']['created'],
        'updated': issue.raw['fields']['updated'],
        'duedate': issue.raw['fields']['duedate'],
        'name': name,
        # 'assignee': issue.raw['fields']['assignee']['displayName'],
        # 'email': issue.raw['fields']['assignee']['emailAddress'],
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


def get_issues(jira, query):
    """
    JIRAから指定されたqueryに合致するissueの一覧を返す
    """
    issues = []
    for issue in jira.search_issues(query):
        issues.append(issue_to_dict(issue))

    return issues


def get_expired_issues(jira, project):
    """
    JIRAから期限切れ、もうすぐ期限切れのissueの一覧をかえす
    """
    # 期限切れ
    expired_query = QUERY.format(project=project, due='due <= "0"')
    expired = get_issues(jira, expired_query)

    # もうすぐ期限切れ
    soon_query = QUERY.format(project=project, due='due > "0" AND due <= 7d')
    soon = get_issues(jira, soon_query)

    return expired, soon


def send_issue_message(title, issues, channel, webhook_url):
    """
    チケットの一覧を Slack に送信する
    """
    # 通知用のテキストを生成
    text = '{}ハ{}件 デス{}\n'.format(title, len(issues), random.choice(FACES))
    for issue in issues:
        text += formatted_issue(issue) + '\n'

    # メッセージを Slack に送信
    payload = {
        'channel': channel,
        'username': 'JIRA bot',
        'icon_emoji': ':jirabot:',
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

    # JIRA に接続
    options = {'server': SERVER}
    jira = JIRA(options=options, basic_auth=(username, password))

    # 対象となるJIRAプロジェクト: slack channelの一覧
    projects = {'HTJ': '#2015',
                'ISSHA': '#committee',
                }
    for project, channel in projects.items():
        # 期限切れ(expired)、もうすぐ期限切れ(soon)のチケット一覧を取得
        expired, soon = get_expired_issues(jira, project)

        url = '<{}/browse/{}|{}> '.format(SERVER, project, project)
        send_issue_message(title=url + '「期限切れチケット」',
                           issues=expired,
                           channel=channel,
                           webhook_url=webhook_url)
        send_issue_message(title=url + '「もうすぐ期限切れチケット」',
                           issues=soon,
                           channel=channel,
                           webhook_url=webhook_url)


if __name__ == '__main__':
    # config.ini からパラメーターを取得
    config = configparser.ConfigParser()
    config.read('config.ini')
    username = config['DEFAULT']['username']
    password = config['DEFAULT']['password']
    webhook_url = config['DEFAULT']['webhook_url']

    main(username, password, webhook_url)
