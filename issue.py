#!/usr/bin/env python

from __future__ import annotations

import configparser
import random
from dataclasses import dataclass

import requests
from jira import JIRA, Issue
from requests.models import Response

# issue を取得する QUERY
QUERY = """project = {project} AND status in (Open, "In Progress", Reopened)
 AND {due} ORDER BY due ASC, component ASC"""

# プロジェクト名とコンポーネント、チャンネルの一覧
PROJECTS = {
    "ISSHA": [
        # (コンポーネント, チャンネル)
        ("一般社団法人", "#committee"),
        ("Python Boot Camp", "#pycamp"),
        ("Pycamp Caravan", "#pycamp-caravan"),
        ("PyCon JP TV", "#pyconjptv準備室"),
    ],
    "USA": [
        ("0. 全体", "#2023"),
        ("1. 予算・会計", "#2023-t-budget"),
        ("2. コンテンツ", "#2023-t-contents"),
        ("3. デザイン", "#2023-t-design"),
        ("4. メディア・広報", "#2023-t-media"),
        ("5. NOC", "#2023-t-noc"),
        ("6. スポンサー", "#2023-t-sponsor"),
        ("7. 配信", "#2023-t-streaming"),
        ("8. システム", "#2023-t-system"),
        ("9.会場", "#2023-t-venue"),
        ("10. チケット", "#2023-t-tickets"),
    ],
}

# プロジェクトのメインチャンネル
PROJECT_CHANNEL = {"ISSHA": "#committee", "USA": "#2023"}

# JIRA サーバー
SERVER = "https://pyconjp.atlassian.net"

# Slack API
SLACK_API = "https://slack.com/api/"

# ロボット顔文字
FACES = ("┗┫￣皿￣┣┛", "┗┃￣□￣；┃┓ ", "┏┫￣皿￣┣┛", "┗┃・ ■ ・┃┛", "┗┫＝皿[＋]┣┛")


@dataclass
class IssueInfo:
    """JIRAの1課題分の情報を保持するクラス"""

    key: str  # 課題のキー(ISSHA-XXXX等)
    url: str  # 課題のURL
    summary: str
    created: str  # 作成日時
    updated: str  # 更新日時
    duedate: str  # 期日
    priority: str  # 優先度
    status: str  # 状態
    components: list
    name: str = ""  # 担当者名
    slack: str = ""  # slackの名前


def issue_to_issue_info(issue: Issue, users: dict[str, str]) -> IssueInfo:
    """
    issue から必要な値を取り出して、IssueInfo形式にして返す
    """
    # コンポーネント名のリストを作成
    components = [component["name"] for component in issue.raw["fields"]["components"]]

    issue_info = IssueInfo(
        key=issue.raw["key"],
        url=issue.permalink(),
        summary=issue.raw["fields"]["summary"],
        created=issue.raw["fields"]["created"],
        updated=issue.raw["fields"]["updated"],
        duedate=issue.raw["fields"]["duedate"],
        priority=issue.raw["fields"]["priority"]["name"],
        status=issue.raw["fields"]["status"]["name"],
        components=components,
    )

    # 担当者が存在する場合はnameに名前を設定する
    assignee = issue.raw["fields"]["assignee"]
    if assignee is not None:
        issue_info.name = assignee.get("displayName")

        # nameがSlackに存在したら、Slackのreal_nameを設定する
        if issue_info.name.lower() in users:
            issue_info.slack = users[issue_info.name.lower()]

    return issue_info


def get_issue_infos(jira: JIRA, query: str, users: dict[str, str]) -> list[IssueInfo]:
    """
    JIRAから指定されたqueryに合致するissueの一覧を返す
    """
    issues = jira.search_issues(query)
    issue_infos = [issue_to_issue_info(issue, users) for issue in issues]

    return issue_infos


def get_expired_issues(
    jira: JIRA, project: str, users: dict[str, str]
) -> tuple[list[IssueInfo], list[IssueInfo]]:
    """
    JIRAから期限切れ、もうすぐ期限切れのissueの一覧をかえす
    """
    # 期限切れ
    expired_query = QUERY.format(project=project, due='due <= "0"')
    expired = get_issue_infos(jira, expired_query, users)

    # もうすぐ期限切れ
    soon_query = QUERY.format(project=project, due='due > "0" AND due <= 7d')
    soon = get_issue_infos(jira, soon_query, users)

    return expired, soon


def get_issue_infos_by_component(
    issue_infos: list[IssueInfo], component: str | tuple[str]
) -> list[IssueInfo]:
    """
    指定されたコンポーネント(複数の場合もある)に関連づいたissue_infoを返す
    """
    # コンポーネントを set に変換する
    if isinstance(component, str):
        component_set = {component}
    else:
        component_set = set(component)

    result = []
    for issue_info in issue_infos:
        # 関連するコンポーネントが存在するissueを抜き出す
        if component_set & set(issue_info.components):
            result.append(issue_info)
    return result


def get_users_from_slack(token: str) -> dict[str, str]:
    """
    Slack上のUserListを取得

    API: https://api.slack.com/methods/users.list
    """
    url = SLACK_API + "users.list"
    payload = {"token": token}

    response = requests.get(url, payload)
    users_list = response.json()

    # real_nameをキー、slackのnameを値にした辞書を作成する
    members = users_list["members"]
    users = {m["profile"].get("real_name").lower(): m["name"] for m in members}

    return users


def formatted_issue_info(issue_info: IssueInfo) -> str:
    """
    1件のissue_infoを文字列にして返す
    """
    issue_text = f"- {issue_info.duedate} <{issue_info.url}|{issue_info.key}>: "
    issue_text += f"{issue_info.summary}"
    if issue_info.slack:
        issue_text += f" (@{issue_info.slack})"
    elif issue_info.name:
        issue_text += f" ({issue_info.name})"
    else:
        issue_text += " (*担当者未設定*)"
    return issue_text


def create_issue_message(title: str, issue_infos: list[IssueInfo]) -> str:
    """
    チケットの一覧をメッセージを作成する
    """
    # 通知用のテキストを生成
    text = f"{title}ハ *{len(issue_infos)}件* デス{random.choice(FACES)}\n"
    text += (
        "> JIRAの氏名(<https://id.atlassian.com/manage-profile|"
        "プロファイルとその公開範囲>)と"
        "SlackのFull nameを同一にするとメンションされるので"
        "おすすめ(大文字小文字は無視)\n"
    )
    for issue_info in issue_infos:
        text += formatted_issue_info(issue_info) + "\n"

    return text


def send_message_to_slack(
    title: str, text: str, channel: str, token: str, debug: bool
) -> Response:
    """
    メッセージを Slack に送信
    """

    url = SLACK_API + "chat.postMessage"
    payload = {
        "token": token,
        "channel": channel,
        "username": "JIRA bot",
        "icon_emoji": ":jirabot:",
        "fallback": title,
        "text": text,
        "mrkdwn": True,
        "link_names": 1,
    }
    # debugモードの場合は slack-test に投げる
    if debug:
        payload["channel"] = "slack-test"
    r = requests.post(url, payload)
    return r


def main(username: str, password: str, token: str, debug: bool) -> None:
    """
    期限切れ、もうすぐ期限切れのチケットの一覧を取得してSlackで通知する
    """

    # JIRA に接続
    options = {"server": SERVER}
    jira = JIRA(options=options, basic_auth=(username, password))

    # Slack から UserListを取得
    users = get_users_from_slack(token)

    # 対象となるJIRAプロジェクト: コンポーネントの一覧
    for project, components in PROJECTS.items():
        # 期限切れ(expired)、もうすぐ期限切れ(soon)のチケット一覧を取得
        pj_expired, pj_soon = get_expired_issues(jira, project, users)

        # プロジェクトごとのチケット状況をまとめる
        summaries = []

        # issueをコンポーネントごとに分ける
        for component, channel in components:
            expired = get_issue_infos_by_component(pj_expired, component)
            soon = get_issue_infos_by_component(pj_soon, component)

            if isinstance(component, tuple):
                component = "、".join(component)

            header = f"*{project}/{component}* の"

            if expired:
                # 期限切れチケットのメッセージを送信
                title = header + "「期限切れチケット」"
                text = create_issue_message(title, expired)
                send_message_to_slack(title, text, channel, token, debug)

            if soon:
                # もうすぐ期限切れチケットのメッセージを送信
                title = header + "「もうすぐ期限切れチケット」"
                text = create_issue_message(title, soon)
                send_message_to_slack(title, text, channel, token, debug)

            # チケット状況を保存
            summaries.append(
                {
                    "component": component,
                    "channel": channel,
                    "expired": len(expired),
                    "soon": len(soon),
                }
            )

        # プロジェクト全体の状況をまとめる
        title = "チケット状況"
        text = f"*{project}* ノチケット状況デス\n"
        for summary in summaries:
            # 残りの件数によって天気マークを付ける
            summary["icon"] = ":sunny:"
            if isinstance(summary["expired"], int):
                if summary["expired"] >= 10:
                    summary["icon"] = ":umbrella:"
                elif summary["expired"] >= 5:
                    summary["icon"] = ":cloud:"

            text += (
                "{icon} *{component}* ({channel}) 期限切れ *{expired}* "
                "もうすぐ期限切れ *{soon}*\n".format(**summary)
            )
        channel = PROJECT_CHANNEL[project]
        send_message_to_slack(title, text, channel, token, debug)


if __name__ == "__main__":
    # config.ini からパラメーターを取得
    config = configparser.ConfigParser()
    config.read("config.ini")
    username = config["DEFAULT"]["username"]
    password = config["DEFAULT"]["password"]
    token = config["DEFAULT"]["token"]
    debug = config["DEFAULT"].getboolean("debug")

    main(username, password, token, debug)
