#!/usr/bin/env python

import configparser
import random

from jira import JIRA
import requests

# issue を取得する QUERY
QUERY = '''project = {project} AND status in (Open, "In Progress", Reopened)
 AND {due} ORDER BY due ASC, component ASC'''

# プロジェクト名とコンポーネント、チャンネルの一覧
PROJECTS = {
    'INU': [
        # (コンポーネント, チャンネル)
        (('0.全体', '9.その他'), '#2018'),
        ('1.事務局', '#t-jimukyoku'),
        ('2.会場', '#t-venue'),
        ('3.システム', '#t-system'),
        ('4.プログラム', '#t-program'),
        ('5.デザイン', '#t-design'),
    ],
    'ISSHA': [
        ('一般社団法人', '#committee'),
        ('Python Boot Camp', '#pycamp'),
    ],
}

# プロジェクトのメインチャンネル
PROJECT_CHANNEL = {
    'INU': '#2018',
    'ISSHA': '#committee'
}

# JIRA サーバー
SERVER = 'https://pyconjp.atlassian.net'

# Slack API
SLACK_API = 'https://slack.com/api/'

# ロボット顔文字
FACES = ('┗┫￣皿￣┣┛', '┗┃￣□￣；┃┓ ',
         '┏┫￣皿￣┣┛', '┗┃・ ■ ・┃┛',
         '┗┫＝皿[＋]┣┛')


def issue_to_dict(issue, users):
    """
    issue から必要な値を取り出して、いい感じの辞書にして返す
    """
    # 担当者が存在しない場合はname,emailをNoneにする
    assignee = issue.raw['fields']['assignee']
    if assignee is None:
        name = None
        email = None
    else:
        name = assignee['name']
        email = assignee['emailAddress']

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
    if email is not None and users is not None:
        issue_dict['slack'] = users.get(email, name)
            
    components = []
    for component in issue.raw['fields']['components']:
        components.append(component['name'])
    issue_dict['components'] = components
    issue_dict['component'] = u", ".join(issue_dict['components'])

    return issue_dict


def get_issues(jira, query, users):
    """
    JIRAから指定されたqueryに合致するissueの一覧を返す
    """
    issues = []
    for issue in jira.search_issues(query):
        issues.append(issue_to_dict(issue, users))

    return issues


def get_expired_issues(jira, project, users):
    """
    JIRAから期限切れ、もうすぐ期限切れのissueの一覧をかえす
    """
    # 期限切れ
    expired_query = QUERY.format(project=project, due='due <= "0"')
    expired = get_issues(jira, expired_query, users)

    # もうすぐ期限切れ
    soon_query = QUERY.format(project=project, due='due > "0" AND due <= 7d')
    soon = get_issues(jira, soon_query, users)

    return expired, soon


def get_issues_by_component(issues, component):
    """
    指定されたコンポーネント(複数の場合もある)に関連づいたissueを返す
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


def get_users_from_slack(token):
    """
    Slack上のUserListを取得
    """
    url = SLACK_API + 'users.list'

    payload = {'token': token}

    response = requests.get(url, payload)
    json = response.json()

    users = {m['profile'].get('email'): m['name'] for m in json['members']}

    return users


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


def send_message_to_slack(title, text, channel, token, debug):
    """
    メッセージを Slack に送信
    """

    url = SLACK_API + 'chat.postMessage'
    payload = {
        'token': token,
        'channel': channel,
        'username': 'JIRA bot',
        'icon_emoji': ':jirabot:',
        'fallback': title,
        'text': text,
        'mrkdwn': True,
        'link_names': 1,
        }
    # debugモードの場合は slack-test に投げる
    if debug:
        payload['channel'] = 'slack-test'
    r = requests.post(url, payload)
    return r


def main(username, password, token, debug):
    """
    期限切れ、もうすぐ期限切れのチケットの一覧を取得してSlackで通知する
    """

    # JIRA に接続
    options = {'server': SERVER}
    jira = JIRA(options=options, basic_auth=(username, password))

    # Slack から UserListを取得
    users = get_users_from_slack(token)

    # 対象となるJIRAプロジェクト: コンポーネントの一覧
    for project, components in PROJECTS.items():
        # 期限切れ(expired)、もうすぐ期限切れ(soon)のチケット一覧を取得
        project_expired, project_soon = get_expired_issues(jira, project, users)

        # プロジェクトごとのチケット状況をまとめる
        summary = []

        # issueをコンポーネントごとに分ける
        for component, channel in components:
            expired = get_issues_by_component(project_expired, component)
            soon = get_issues_by_component(project_soon, component)

            if isinstance(component, tuple):
                component = '、'.join(component)

            header = '*{}/{}* の'.format(project, component)

            # 期限切れチケットのメッセージを送信
            title = header + '「期限切れチケット」'
            text = create_issue_message(title, expired)
            send_message_to_slack(title, text, channel, token, debug)

            # もうすぐ期限切れチケットのメッセージを送信
            title = header + '「もうすぐ期限切れチケット」'
            text = create_issue_message(title, soon)
            send_message_to_slack(title, text, channel, token, debug)

            # チケット状況を保存
            summary.append({'component': component,
                            'channel': channel,
                            'expired': len(expired),
                            'soon': len(soon),
                            })

        # プロジェクト全体の状況をまとめる
        title = 'チケット状況'
        text = '*{}* ノチケット状況デス\n'.format(project)
        for component in summary:
            # 残りの件数によって天気マークを付ける
            component['icon'] = ':sunny:'
            if component['expired'] >= 10:
                component['icon'] = ':umbrella:'
            elif component['expired'] >= 5:
                component['icon'] = ':cloud:'

            text += '{icon} *{component}* ({channel}) 期限切れ *{expired}* '\
                    'もうすぐ期限切れ *{soon}*\n'.format(**component)
        channel = PROJECT_CHANNEL[project]
        send_message_to_slack(title, text, channel, token, debug)


if __name__ == '__main__':
    # config.ini からパラメーターを取得
    config = configparser.ConfigParser()
    config.read('config.ini')
    username = config['DEFAULT']['username']
    password = config['DEFAULT']['password']
    token = config['DEFAULT']['token']
    debug = config['DEFAULT'].getboolean('debug')

    main(username, password, token, debug)
