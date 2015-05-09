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

# プロジェクト名とコンポーネント、チャンネルの一覧
PROJECTS = {
    'HTJ': {
        # コンポーネント: チャンネル
        '会場': '#t-venue',
        '事務局': '#t-jimukyoku',
        'プログラム': '#t-program',
        'メディア': '#t-media',
        ('全体', '環境', 'その他'): '#2015',
    },
    'ISSHA': {
        '一般社団法人': '#committee',
        'PyCon mini 札幌': '#mini-sapporo',
        'PyCon mini 広島': '#mini-hiroshima',
    },
}
PROJECT_CHANNEL = {
    'HTJ': '#2015',
    'ISSHA': '#committee'
}

# JIRAとSlackで id が違う人の対応表
JIRA_SLACK = {
    # JIRA ID: slack ID
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
    'angela': 'sayaka_angela',
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


def get_issues_by_component(issues, component):
    """指定されたコンポーネント(複数の場合もある)に関連づいたissueを返す
    """
    result = []
    for issue in issues:
        # コンポーネントを set に変換する
        if isinstance(component, str):
            component = {component}
        else:
            component = set(component)

        # 関連するコンポーネントが存在するissueを抜き出す
        if len(component & set(issue['components'])) > 0:
            result.append(issue)
    return result


def formatted_issue(issue_dict):
    """
    1件のissueを文字列にして返す
    """
    issue_text = u"- {duedate} <{url}|{key}>: {summary}(@{slack})"
    return issue_text.format(**issue_dict)


def create_issue_message(title, issues):
    """
    チケットの一覧をメッセージを作成する
    """
    # 通知用のテキストを生成
    text = '{}ハ *{}件* デス{}\n'.format(title, len(issues), random.choice(FACES))
    for issue in issues:
        text += formatted_issue(issue) + '\n'

    return text


def send_message_to_slack(title, text, channel, webhook_url):
    """
    メッセージを Slack に送信
    """

    payload = {
        'channel': channel,
        'username': 'JIRA bot',
        'icon_emoji': ':jirabot:',
        'fallback': title,
        'text': text,
        'mrkdwn': True,
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

    # 対象となるJIRAプロジェクト: コンポーネントの一覧
    for project, components in PROJECTS.items():
        # 期限切れ(expired)、もうすぐ期限切れ(soon)のチケット一覧を取得
        project_expired, project_soon = get_expired_issues(jira, project)

        # プロジェクトごとのチケット状況をまとめる
        summary = []

        # issueをコンポーネントごとに分ける
        for component, channel in components.items():
            expired = get_issues_by_component(project_expired, component)
            soon = get_issues_by_component(project_soon, component)

            if isinstance(component, tuple):
                component = '、'.join(component)

            header = '*{}* の'.format(component)

            # 期限切れチケットのメッセージを送信
            title = header + '「期限切れチケット」'
            text = create_issue_message(title, expired)
            send_message_to_slack(title, text, channel, webhook_url)

            # もうすぐ期限切れチケットのメッセージを送信
            title = header + '「もうすぐ期限切れチケット」'
            text = create_issue_message(title, soon)
            send_message_to_slack(title, text, channel, webhook_url)

            # チケット状況を保存
            summary.append({'component': component,
                            'channel': channel,
                            'expired': len(expired),
                            'soon': len(soon),
                            })

        # プロジェクト全体の状況をまとめる
        title = 'チケット状況'
        text = 'チケットノ状況デス\n'
        for component in summary:
            # 残りの件数によって天気マークを付ける
            component['icon'] = ':sunny:'
            if component['expired'] >= 10:
                component['icon'] = ':umbrella:'
            elif component['expired'] >= 5:
                component['icon'] = ':cloud:'

            text += '{icon} *{component}* ({channel}) 期限切れ *{expired}* もうすぐ期限切れ *{soon}*\n'.format(**component)
        channel = PROJECT_CHANNEL[project]
        send_message_to_slack(title, text, channel, webhook_url)

if __name__ == '__main__':
    # config.ini からパラメーターを取得
    config = configparser.ConfigParser()
    config.read('config.ini')
    username = config['DEFAULT']['username']
    password = config['DEFAULT']['password']
    webhook_url = config['DEFAULT']['webhook_url']

    main(username, password, webhook_url)
