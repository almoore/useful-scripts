#!/usr/bin/env python3
# python3 -m pip install tabulate pyyaml

import boto3
import argparse
from tabulate import tabulate
import yaml


def get_rds_clusters_with_versions(
    engine_filter=None,
    identifier_filter=None,
    major_version_filter=None,
    region="us-east-1",
    output_format="table",
):
    # Initialize a session using Amazon RDS
    client = boto3.client("rds", region_name=region)

    # Use paginator for handling large numbers of clusters
    paginator = client.get_paginator("describe_db_clusters")
    page_iterator = paginator.paginate()

    # Extract and filter DB cluster information
    filtered_clusters = []
    for page in page_iterator:
        for cluster in page["DBClusters"]:
            db_cluster_identifier = cluster["DBClusterIdentifier"]
            db_engine = cluster["Engine"]
            db_engine_version = cluster["EngineVersion"]
            major_version = db_engine_version.split(".")[0]
            db_endpoint = cluster["Endpoint"]

            if (
                (engine_filter and engine_filter != db_engine)
                or (
                    identifier_filter
                    and identifier_filter not in db_cluster_identifier
                )
                or (major_version_filter and major_version_filter != major_version)
            ):
                continue

            filtered_clusters.append(
                {
                    "Identifier": db_cluster_identifier,
                    "Engine": db_engine,
                    "Version": db_engine_version,
                    "Endpoint": db_endpoint,
                }
            )
            # filtered_clusters.append(cluster)

    # Output formatting
    if output_format == "table":
        if filtered_clusters:
            headers = ["Identifier", "Engine", "Version"]
            table = [
                [inst["Identifier"], inst["Engine"], inst["Version"]]
                for inst in filtered_clusters
            ]
            print(tabulate(table, headers, tablefmt="grid"))
        else:
            print("No clusters match your filters.")

    elif output_format == "yaml":
        print(yaml.dump(filtered_clusters, default_flow_style=False))

    elif output_format == "name":
        for inst in filtered_clusters:
            print(inst["Identifier"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter RDS clusters by engine type, cluster identifier, major version, and output format."
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
        help="Partial or full filter by database cluster identifier.",
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

    get_rds_clusters_with_versions(
        engine_filter=args.engine,
        identifier_filter=args.identifier,
        major_version_filter=args.version,
        region=args.region,
        output_format=args.output,
    )
