#!/usr/bin/env python3
# python3 -m pip install tabulate pyyaml

import boto3
import argparse
from tabulate import tabulate
import yaml


def get_rds_instances_with_versions(
    engine_filter=None,
    identifier_filter=None,
    major_version_filter=None,
    region="us-east-1",
    output_format="table",
):
    # Initialize a session using Amazon RDS
    client = boto3.client("rds", region_name=region)

    # Use paginator for handling large numbers of instances
    paginator = client.get_paginator("describe_db_clusters")
    page_iterator = paginator.paginate()

    # Extract and filter DB instance information
    filtered_instances = []
    for page in page_iterator:
        for instance in page["DBClusters"]:
            db_cluster_identifier = instance["DBClusterIdentifier"]
            db_engine = instance["Engine"]
            db_engine_version = instance["EngineVersion"]
            major_version = db_engine_version.split(".")[0]

            if (
                (engine_filter and engine_filter != db_engine)
                or (
                    identifier_filter
                    and identifier_filter not in db_cluster_identifier
                )
                or (major_version_filter and major_version_filter != major_version)
            ):
                continue

            filtered_instances.append(
                {
                    "Identifier": db_cluster_identifier,
                    "Engine": db_engine,
                    "Version": db_engine_version,
                }
            )

    # Output formatting
    if output_format == "table":
        if filtered_instances:
            headers = ["Identifier", "Engine", "Version"]
            table = [
                [inst["Identifier"], inst["Engine"], inst["Version"]]
                for inst in filtered_instances
            ]
            print(tabulate(table, headers, tablefmt="grid"))
        else:
            print("No instances match your filters.")

    elif output_format == "yaml":
        print(yaml.dump(filtered_instances, default_flow_style=False))

    elif output_format == "name":
        for inst in filtered_instances:
            print(inst["Identifier"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter RDS instances by engine type, instance identifier, major version, and output format."
    )
    parser.add_argument(
        "-e",
        "--engine",
        type=str,
        help="Filter by database engine type (e.g., 'postgres').",
    )
    parser.add_argument(
        "-i",
        "--identifier",
        type=str,
        help="Partial or full filter by database instance identifier.",
    )
    parser.add_argument(
        "-v",
        "--version",
        type=str,
        help="Filter by major version of the database engine (e.g., '13').",
    )
    parser.add_argument(
        "--region", type=str, default="us-east-1", help="AWS region to query against."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="table",
        choices=["table", "yaml", "name"],
        help="Output format: 'table', 'yaml', or 'name'.",
    )

    args = parser.parse_args()

    get_rds_instances_with_versions(
        engine_filter=args.engine,
        identifier_filter=args.identifier,
        major_version_filter=args.version,
        region=args.region,
        output_format=args.output,
    )
