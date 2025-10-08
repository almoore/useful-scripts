#!/usr/bin/env python3
import boto3


def get_default_postgres_versions():
    # Initialize a session using Amazon RDS
    client = boto3.client('rds', region_name='us-east-1')  # You can specify your preferred AWS region here

    # Retrieve a list of available DB engine versions for PostgreSQL
    response = client.describe_db_engine_versions(Engine='postgres')
    major_versions = set(v['EngineVersion'].split('.')[0] for v in response['DBEngineVersions'])

    # Dictionary to store the default version for each major version
    default_versions = {}
    print("Fetching default engine version for each major version:")
    for major_version in sorted(list(major_versions)):

        try:
            response = client.describe_db_engine_versions(
                Engine='postgres',
                EngineVersion=major_version,
                DefaultOnly=True
            )
            if response['DBEngineVersions']:
                default_versions[major_version] = response['DBEngineVersions'][0]['EngineVersion']
        except Exception as e:
            print(f"Could not find default version for major version {major_version}: {e}")    # Iterate over engine versions to collect default version

    return default_versions


def get_latest_postgres_versions():
    # Initialize a session using Amazon RDS
    client = boto3.client('rds', region_name='us-east-1')  # You can specify your preferred AWS region here

    # Retrieve a list of available DB engine versions for PostgreSQL
    response = client.describe_db_engine_versions(
        Engine='postgres',
        DefaultOnly=False  # Set to False to get information about all versions
    )

    # Dictionary to store the latest version for each major version
    latest_versions = {}

    # Iterate over engine versions
    for engine in response['DBEngineVersions']:
        engine_version = engine['EngineVersion']
        major_version = engine_version.split('.')[0]  # Get the major version (e.g., '13' from '13.4')

        # Compare and store the latest version for each major version
        if major_version not in latest_versions or compare_versions(engine_version, latest_versions[major_version]) > 0:
            latest_versions[major_version] = engine_version

    return latest_versions


def compare_versions(version1, version2):
    def parse_version(version):
        # Split the version string and extract numeric components
        return [int(part.split('-')[0]) for part in version.split('.')]

    v1_parts = parse_version(version1)
    v2_parts = parse_version(version2)

    # Compare each part of the versions
    for v1, v2 in zip(v1_parts, v2_parts):
        if v1 > v2:
            return 1
        elif v1 < v2:
            return -1
    
    # If all parts are equal, check if one version has extra depth
    if len(v1_parts) > len(v2_parts):
        return 1
    elif len(v1_parts) < len(v2_parts):
        return -1

    return 0


if __name__ == "__main__":
    latest_versions = get_latest_postgres_versions()
    default_versions = get_default_postgres_versions()
    print("Latest RDS PostgreSQL version for each supported major version:")
    for major_version, version in latest_versions.items():
        print(f"PostgreSQL {major_version}.x: {version}")
    print("Default stable RDS PostgreSQL version for each supported major version:")
    for major_version, version in default_versions.items():
        print(f"PostgreSQL {major_version}.x: {version}")
