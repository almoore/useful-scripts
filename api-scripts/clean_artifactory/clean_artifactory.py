#!/usr/bin/env python3

import requests
import pprint
from vercmp import debian_compare
from retrying import retry
import urllib3
import os
import argparse
from artifactory_artifacts import DebianArtifact

def search_artifactory(aql, baseurl, apikey=None, verify=True):
    headers = {"X-Jfrog-Art-Api": apikey}
    r = requests.post(
        url=f"http://{baseurl}/artifactory/api/search/aql",
        headers=headers,
        data=aql,
        verify=verify
    )
    r.raise_for_status()
    response_data = r.json()
    results = response_data["results"]
    return results


def determine_deletables(artifacts):
    groups = {}
    for artifact in artifacts:
        properties = {}
        for prop in artifact["properties"]:
            properties[prop["key"]] = prop["value"]

        artifact_record = DebianArtifact(
            artifact["name"], artifact["repo"], artifact["path"], properties
        )

        group_key = "/".join([artifact["repo"], properties["deb.name"]])

        if group_key not in groups:
            groups[group_key] = []

        groups[group_key].append(artifact_record)
    deletables = []
    for groupk, groupv in groups.items():
        if len(groupv) > 3:
            sorted_pkgs = sorted(groupv, reverse=True)
            print("Keeping {0}...".format(sorted_pkgs[0]))
            print("Keeping {0}...".format(sorted_pkgs[1]))
            print("Keeping {0}...".format(sorted_pkgs[2]))
            deletables.extend(sorted_pkgs[3:])
    return deletables


@retry(stop_max_attempt_number=7, wait_fixed=2000, apikey=None, verify=True)
def delete_package(package, baseurl):
    headers = {"X-Jfrog-Art-Api": apikey}
    print("Deleting {0}...".format(package))
    r = requests.delete(
        url=f"http://{baseurl}/artifactory/{package}",
        headers=headers,
        verify=verify
    )
    r.raise_for_status()


def delete_packages(packages):
    for package in packages:
        delete_package(package)


def main():
    baseurl = os.environ.get("ARTIFACTORY_REGISTRY")
    apikey  = os.environ.get("ARTIFACTORY_API_KEY")
    aql =  """
    items.find({
        "property.key": "deb.name",
        "property.value": {"$match": "*"}
    }).include("name", "path", "repo", "property")
    """
    docker_query = """items.find({
      "type": "file", 
      "repo": "docker-local"
      "stat.downloaded": {"$before":"4w"},
    }).include("name", "@docker.repoName", "@docker.manifest" ,"stat.downloads")
    """
    results = search_artifactory(aql=aql, baseurl=baseurl, apikey=apikey, verify=False)
    # docker_results = search_artifactory(aql=docker_query, baseurl=baseurl, apikey=apikey, verify=False)
    print("Sample result:")
    print("")
    pprint.pprint(next(iter(results), None))
    print("")
    artifacts = determine_deletables(results)
    #delete_packages(artifacts)
    pprint.pprint(artifacts)


if __name__ == "__main__":
    main()
