import json
from asyncio import gather
from typing import List

from httpx import AsyncClient, BasicAuth

from release_notes_generator.configuration import Configuration
from release_notes_generator.state import (
    GitHubRelease,
    JiraTicket,
    ReleaseNotesStateInput,
    SectionState,
)


async def get_jira_tickets(state: ReleaseNotesStateInput, config: Configuration):
    auth = BasicAuth(username=config.jira_user_email, password=config.jira_api_key)
    headers = {"Accept": "application/json"}
    pagination_start = 0

    async with AsyncClient(auth=auth, headers=headers) as client:
        jql_query = (
            f"project = '{config.jira_project_key}' AND "
            f"created >= -{state.days_filter}d and status IN ('Done/In prod', 'Done')"
        )
        url = render_request_url(config.jira_host, jql_query, pagination_start)

        response = await client.get(url)

        responses = [json.loads(response.text)]
        pagination_tasks = []

        if responses[0].get("total", 0) > responses[0].get("maxResults", 0):
            while pagination_start < responses[0].get("total", 0):
                pagination_start += responses[0].get("maxResults", 0)
                pagination_tasks.append(
                    client.get(
                        render_request_url(
                            config.jira_host, jql_query, pagination_start
                        )
                    )
                )

        for response in await gather(*pagination_tasks):
            responses.append(json.loads(response.text))

    return convert_jira_tickets(responses)


def render_request_url(host: str, jql: str, start: int):
    return f"https://{host}/rest/api/3/search?jql={jql}&startAt={start}"


def convert_jira_tickets(responses: List[dict]):
    tickets = []
    for response in responses:
        for ticket in response.get("issues", [{}]):
            tickets.append(
                JiraTicket(
                    name=ticket.get("fields", {}).get("summary", ""),
                    description=str(ticket.get("fields", {}).get("description", {})),
                    status=ticket.get("fields", {}).get("status", {}).get("name", ""),
                    epic=ticket.get("fields", {})
                    .get("parent", {})
                    .get("fields", {})
                    .get("summary", ""),
                )
            )
    return tickets


async def get_github_releases(config: Configuration):
    async with AsyncClient() as client:
        release_tasks = [
            load_and_parse_release(config, client, repo) for repo in config.github_repos
        ]
        releases = await gather(*release_tasks)

        return {release.repo: release for release in releases}


async def load_and_parse_release(
    config: Configuration, client: AsyncClient, repo_name: str
):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {config.github_api_key}",
    }

    response = await client.get(
        f"https://api.github.com/repos/{repo_name}/releases", headers=headers
    )
    releases = json.loads(response.text)

    if len(releases) > 1:
        diff_headers = {
            "Accept": "text/plain",
            "Authorization": f"Bearer {config.github_api_key}",
        }
        diff_response = await client.get(
            f"https://github.com/{repo_name}/compare/{releases[1]['tag_name']}...{releases[0]['tag_name']}.diff",
            headers=diff_headers,
        )
        return GitHubRelease(
            repo=repo_name,
            description=releases[0].get("body", "No description was provided."),
            diff=diff_response.text,
        )
    elif len(releases) > 0:
        return GitHubRelease(
            repo=repo_name,
            description=releases[0].get("body", "No description was provided."),
            diff="No diff was provided.",
        )  # TODO handling diff for the first tag
    else:
        return GitHubRelease(
            repo=repo_name,
            description="No description was provided.",
            diff="No diff was provided.",
        )


def get_diff_tools(state: SectionState):
    diff_tools = []
    for release in state.github_releases.values():
        diff_tools.append(
            {
                "type": "function",
                "function": {
                    "name": release.repo,
                    "description": f"Get difference between two last releases of "
                    f"{release.repo} repo and latest release description.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            }
        )
    return diff_tools
