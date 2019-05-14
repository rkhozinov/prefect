import click
import pendulum
from tabulate import tabulate

from prefect import config
from prefect.client import Client
from prefect.utilities.cli import open_in_playground
from prefect.utilities.graphql import with_args, EnumValue


@click.group(hidden=True)
def get():
    """
    Get commands that refer to querying Prefect Cloud metadata.

    \b
    Usage:
        $ prefect get [OBJECT]

    \b
    Arguments:
        flow-runs   Query flow runs
        flows       Query flows
        projects    Query projects
        tasks       Query tasks

    \b
    Examples:
        $ prefect get flows
        NAME      VERSION   PROJECT NAME   AGE
        My-Flow   3         My-Project     3 days ago

    \b
        $ prefect get flows --project New-Proj --all-versions
        NAME        VERSION   PROJECT NAME   AGE
        Test-Flow   2         New-Proj       22 hours ago
        Test-Flow   1         New-Proj       1 month ago

    \b
        $ prefect get tasks --flow-name Test-Flow
        NAME          FLOW NAME   FLOW VERSION   AGE          MAPPED   TYPE
        first_task    Test-Flow   1              5 days ago   False    prefect.tasks.core.function.FunctionTask
        second_task   Test-Flow   1              5 days ago   True     prefect.tasks.core.function.FunctionTask
    """
    pass


@get.command(hidden=True)
@click.option("--name", "-n", help="A flow name to query.")
@click.option("--version", "-v", type=int, help="A flow version to query.")
@click.option("--project", "-p", help="The name of a project to query.")
@click.option("--limit", "-l", default=10, help="A limit amount of tasks to query.")
@click.option("--all-versions", is_flag=True, help="Query all flow versions.")
@click.option("--playground", is_flag=True, help="Open this query in the playground.")
def flows(name, version, project, limit, all_versions, playground):
    """
    Query information regarding your Prefect flows.
    """

    distinct_on = EnumValue("name")
    if all_versions:
        distinct_on = None

    query = {
        "query": {
            with_args(
                "flow",
                {
                    "where": {
                        "_and": {
                            "name": {"_eq": name},
                            "version": {"_eq": version},
                            "project": {"name": {"_eq": project}},
                        }
                    },
                    "order_by": {
                        "name": EnumValue("asc"),
                        "version": EnumValue("desc"),
                    },
                    "distinct_on": distinct_on,
                    "limit": limit,
                },
            ): {
                "name": True,
                "version": True,
                "project": {"name": True},
                "created": True,
            }
        }
    }

    if playground:
        open_in_playground(query)
        return

    result = Client().graphql(query)

    flow_data = result.data.flow

    output = []
    for item in flow_data:
        output.append(
            [
                item.name,
                item.version,
                item.project.name,
                pendulum.parse(item.created).diff_for_humans(),
            ]
        )

    click.echo(
        tabulate(
            output,
            headers=["NAME", "VERSION", "PROJECT NAME", "AGE"],
            tablefmt="plain",
            numalign="left",
            stralign="left",
        )
    )


@get.command(hidden=True)
@click.option("--name", "-n", help="A project name to query.")
@click.option("--playground", is_flag=True, help="Open this query in the playground.")
def projects(name, playground):
    """
    Query information regarding your Prefect projects.
    """
    query = {
        "query": {
            with_args(
                "project",
                {
                    "where": {"_and": {"name": {"_eq": name}}},
                    "order_by": {"name": EnumValue("asc")},
                },
            ): {
                "name": True,
                "created": True,
                "description": True,
                with_args("flows_aggregate", {"distinct_on": EnumValue("name")}): {
                    EnumValue("aggregate"): EnumValue("count")
                },
            }
        }
    }

    if playground:
        open_in_playground(query)
        return

    result = Client().graphql(query)

    project_data = result.data.project

    output = []
    for item in project_data:
        output.append(
            [
                item.name,
                item.flows_aggregate.aggregate.count,
                pendulum.parse(item.created).diff_for_humans(),
                item.description,
            ]
        )

    click.echo(
        tabulate(
            output,
            headers=["NAME", "FLOW COUNT", "AGE", "DESCRIPTION"],
            tablefmt="plain",
            numalign="left",
            stralign="left",
        )
    )


@get.command(hidden=True)
@click.option("--limit", "-l", default=10, help="A limit amount of flow runs to query.")
@click.option("--flow", "-f", help="Specify a flow's runs to query.")
@click.option("--project", "-p", help="Specify a project's runs to query.")
@click.option("--started", "-s", is_flag=True, help="Only retrieve started flow runs.")
@click.option("--playground", is_flag=True, help="Open this query in the playground.")
def flow_runs(limit, flow, project, started, playground):
    """
    Query information regarding Prefect flow runs.
    """

    if started:
        order = {"start_time": EnumValue("desc")}

        where = {
            "_and": {
                "flow": {
                    "_and": {
                        "name": {"_eq": flow},
                        "project": {"name": {"_eq": project}},
                    }
                },
                "start_time": {"_is_null": False},
            }
        }
    else:
        order = {"created": EnumValue("desc")}

        where = {
            "flow": {
                "_and": {"name": {"_eq": flow}, "project": {"name": {"_eq": project}}}
            }
        }

    query = {
        "query": {
            with_args(
                "flow_run", {"where": where, "limit": limit, "order_by": order}
            ): {
                "flow": {"name": True},
                "created": True,
                "state": True,
                "name": True,
                "duration": True,
                "start_time": True,
            }
        }
    }

    if playground:
        open_in_playground(query)
        return

    result = Client().graphql(query)

    flow_run_data = result.data.flow_run

    output = []
    for item in flow_run_data:
        start_time = (
            pendulum.parse(item.start_time).to_datetime_string()
            if item.start_time
            else None
        )
        output.append(
            [
                item.name,
                item.flow.name,
                item.state,
                pendulum.parse(item.created).diff_for_humans(),
                start_time,
                item.duration,
            ]
        )

    click.echo(
        tabulate(
            output,
            headers=["NAME", "FLOW NAME", "STATE", "AGE", "START TIME", "DURATION"],
            tablefmt="plain",
            numalign="left",
            stralign="left",
        )
    )


@get.command(hidden=True)
@click.option("--name", "-n", help="A task name to query")
@click.option("--flow-name", "-fn", help="A flow name to query")
@click.option("--flow-version", "-fv", type=int, help="A flow version to query.")
@click.option("--project", "-p", help="The name of a project to query.")
@click.option("--limit", "-l", default=10, help="A limit amount of tasks to query.")
@click.option("--playground", is_flag=True, help="Open this query in the playground.")
def tasks(name, flow_name, flow_version, project, limit, playground):
    """
    Query information regarding your Prefect tasks.
    """

    query = {
        "query": {
            with_args(
                "task",
                {
                    "where": {
                        "_and": {
                            "name": {"_eq": name},
                            "flow": {
                                "name": {"_eq": flow_name},
                                "project": {"name": {"_eq": project}},
                                "version": {"_eq": flow_version},
                            },
                        }
                    },
                    "limit": limit,
                    "order_by": {"created": EnumValue("desc")},
                },
            ): {
                "name": True,
                "created": True,
                "flow": {"name": True, "version": True},
                "mapped": True,
                "type": True,
            }
        }
    }

    if playground:
        open_in_playground(query)
        return

    result = Client().graphql(query)

    task_data = result.data.task

    output = []
    for item in task_data:
        output.append(
            [
                item.name,
                item.flow.name,
                item.flow.version,
                pendulum.parse(item.created).diff_for_humans(),
                item.mapped,
                item.type,
            ]
        )

    click.echo(
        tabulate(
            output,
            headers=["NAME", "FLOW NAME", "FLOW VERSION", "AGE", "MAPPED", "TYPE"],
            tablefmt="plain",
            numalign="left",
            stralign="left",
        )
    )