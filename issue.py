#!/usr/bin/env python
# -*- coding: utf-8 -*-

from jira.client import JIRA
from pit import Pit
import pprint

def issue_to_dict(issue):
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

def print_issue(issue_dict):
    print u"{key}: {summary} {duedate} {name} {priority} {status} {component}".format(**issue_dict)

def main(jira):
    # 期限切れの issue を取得
    for issue in jira.search_issues('project = UMA AND status in (Open, "In Progress", Reopened) AND due <= "0" ORDER BY component ASC, due ASC'):
        issue_dict = issue_to_dict(issue)
        print_issue(issue_dict)

    #pp = pprint.PrettyPrinter(indent=2)
    #pp.pprint(issue.raw)
    
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

