import json
from asyncio import gather
from typing import List

from httpx import AsyncClient, BasicAuth

from release_notes_generator.configuration import Configuration
from release_notes_generator.state import JiraTicket, ReleaseNotesStateInput


async def get_jira_tickets(state: ReleaseNotesStateInput, config: Configuration):
    auth = BasicAuth(username=config.jira_user_email, password=config.jira_api_key)
    headers = {"Accept": "application/json"}
    pagination_start = 0

    async with AsyncClient(auth=auth, headers=headers) as client:
        jql_query = (
            f"project = '{config.jira_project_key}' AND "
            f"created >= -{state.days_filter}d and status = 'Done/In prod'"
        )
        url = render_request_url(config.jira_host, jql_query, pagination_start)

        response = await client.get(url)

        responses = [json.loads(response.text)]
        pagination_tasks = []

        if responses[0]["total"] > responses[0]["maxResults"]:
            while pagination_start < responses[0]["total"]:
                pagination_start += responses[0]["maxResults"]
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
        for ticket in response["issues"]:
            parent = ticket["fields"].get("parent")
            tickets.append(
                JiraTicket(
                    name=ticket["fields"]["summary"],
                    description=str(ticket["fields"]["description"]),
                    status=ticket["fields"]["status"]["name"],
                    epic=parent["fields"]["summary"] if parent else "",
                )
            )
    return tickets


async def get_github_data(): ...
