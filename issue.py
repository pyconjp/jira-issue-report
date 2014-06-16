#!/usr/bin/env python
# -*- coding: utf-8 -*-

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pit import Pit
from jira.client import JIRA

# 期限切れ
EXPIRED_QUERY = 'project = UMA AND status in (Open, "In Progress", Reopened) AND due <= "0" ORDER BY due ASC, component ASC'
# 一週間後に期限切れ
WEEK_QUERY = 'project = UMA AND status in (Open, "In Progress", Reopened) AND due >= "0" AND due > "0" AND due <= 7d ORDER BY due ASC, component ASC'

def issue_to_dict(issue):
    """
    issue から必要な値を取り出して、辞書に入れて返す
    """
    issue_dict = {
        'key': issue.raw['key'],
        'url': issue.self,
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

    components = []
    for component in issue.raw['fields']['components']:
        components.append(component['name'])
    issue_dict['components'] = components
    issue_dict['component'] = u", ".join(issue_dict['components'])

    return issue_dict

def formatted_issue(issue_dict):
    """
    1件のissueを
    """
    return u"""- {duedate} {key}: {summary}({name})
""".format(**issue_dict)

def main(jira):

    # 期限切れの issue を取得
    issues = []

    text = u"""https://pyconjp.atlassian.net/

期限切れチケット
----------------
"""
    for issue in jira.search_issues(EXPIRED_QUERY):
        text += formatted_issue(issue_to_dict(issue))

    text += u"""
あと一週間で期限切れチケット
----------------------------
"""
    for issue in jira.search_issues(WEEK_QUERY):
        text += formatted_issue(issue_to_dict(issue))

    #print text
    me = 'takanori@pycon.jp'
    you = 'takanori@takanory.net'

    msg = MIMEText(text.encode('utf-8'), 'plain', 'utf-8')
    msg['Subject'] = u'PyCon JP 2014 の期限切れチケット一覧'
    msg['From'] = me
    msg['To'] = you

    server = smtplib.SMTP('localhost')
    server.sendmail(me, [you], msg.as_string())
    
if __name__ == '__main__':
    # ユーザー名とパスワードを取得
    conf = Pit.get('jira',
                   {'require':{'username':'username','password':'password'}})

    options = {
        'server': 'https://pyconjp.atlassian.net'
        }
    jira = JIRA(options=options,
                basic_auth=(conf['username'], conf['password']))
    main(jira)

