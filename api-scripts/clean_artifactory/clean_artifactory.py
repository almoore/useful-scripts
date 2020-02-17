#r!/usr/bin/python

import requests
import pprint
from vercmp import debian_compare
from retrying import retry

class DebianArtifact:
    def __init__(self,name,repo,path,properties):
        self.filename = name
        self.repo = repo
        self.properties = properties
        self.path = path
        self.name = properties['deb.name']
        self.version = properties['deb.version']

    def as_dict(self):
        return {
                'filename': self.filename,
                'repo': self.repo,
                'properties': self.properties,
                'path': self.path,
                'name': self.name,
                'version': self.version
                }

    def __str__(self):
        return '/'.join([self.repo, self.path, self.filename])

    def __lt__(self, other):
        if self.name == other.name:
            return debian_compare(self.version, other.version) < 0
        else:
            return self.name < other.name

    def __le__(self, other):
        if self.name == other.name:
            return debian_compare(self.version, other.version) <= 0
        else:
            return self.name <= other.name

    def __eq__(self, other):
        if self.name == other.name:
            return debian_compare(self.version, other.version) == 0
        else:
            return False

    def __ne__(self, other):
        if self.name == other.name:
            return debian_compare(self.version, other.version) != 0
        else:
            return True

    def __ge__(self, other):
        if self.name == other.name:
            return debian_compare(self.version, other.version) >= 0
        else:
            return self.name >= other.name

    def __gt__(self, other):
        if self.name == other.name:
            return debian_compare(self.version, other.version)
        else:
            return self.name > other.name

def search_artifactory(aql):
    headers = {'X-Jfrog-Art-Api': 'APIKEYHEREPLEASE'}
    r = requests.post(url='http://p-artifactory.imovetv.com/artifactory/api/search/aql',
            headers=headers, data=aql)
    r.raise_for_status()
    response_data = r.json()
    results = response_data['results']
    return results

def determine_deletables(artifacts):
    groups = {}
    for artifact in artifacts:
        properties = {}
        for prop in artifact['properties']:
            properties[ prop['key'] ] = prop['value']

        artifact_record = DebianArtifact(artifact['name'], artifact['repo'], artifact['path'], properties)

        group_key = '/'.join([artifact['repo'], properties['deb.name']])

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

@retry(stop_max_attempt_number=7, wait_fixed=2000)
def delete_package(package):
    headers = {'X-Jfrog-Art-Api': 'APIKEYHEREPLEASE'}
    print("Deleting {0}...".format(package))
    r = requests.delete(url='http://p-artifactory.imovetv.com/artifactory/' + str(package),
            headers=headers)
    r.raise_for_status()

def delete_packages(packages):
    for package in packages:
        delete_package(package)

def main():
    results = search_artifactory('''
items.find({
    "property.key": "deb.name",
    "property.value": {"$match": "salt-state-*"}
}).include("name", "path", "repo", "property")
''')
    print("Sample result:")
    print("")
    pprint.pprint(results[0])
    print("")
    artifacts = determine_deletables(results)
    delete_packages(artifacts)
    #pprint.pprint(sift_artifacts(results))

if __name__ == '__main__':
    main()
