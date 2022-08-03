class DebianArtifact:
    def __init__(self, name, repo, path, properties):
        self.filename = name
        self.repo = repo
        self.properties = properties
        self.path = path
        self.name = properties["deb.name"]
        self.version = properties["deb.version"]

    def as_dict(self):
        return {
            "filename": self.filename,
            "repo": self.repo,
            "properties": self.properties,
            "path": self.path,
            "name": self.name,
            "version": self.version,
        }

    def __str__(self):
        return "/".join([self.repo, self.path, self.filename])

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

class DockerArtifact:
    def __init__(self, name, repo, path, properties):
        self.filename = name
        self.repo = repo
        self.properties = properties
        self.path = path
        self.name = properties["name"]
        self.version = properties["version"]

    def as_dict(self):
        return {
            "filename": self.filename,
            "repo": self.repo,
            "properties": self.properties,
            "path": self.path,
            "name": self.name,
            "version": self.version,
        }

    def __str__(self):
        return "/".join([self.repo, self.path, self.filename])

    def __lt__(self, other):
        if self.name == other.name:
            return docker_compare(self.version, other.version) < 0
        else:
            return self.name < other.name

    def __le__(self, other):
        if self.name == other.name:
            return docker_compare(self.version, other.version) <= 0
        else:
            return self.name <= other.name

    def __eq__(self, other):
        if self.name == other.name:
            return docker_compare(self.version, other.version) == 0
        else:
            return False

    def __ne__(self, other):
        if self.name == other.name:
            return docker_compare(self.version, other.version) != 0
        else:
            return True

    def __ge__(self, other):
        if self.name == other.name:
            return docker_compare(self.version, other.version) >= 0
        else:
            return self.name >= other.name

    def __gt__(self, other):
        if self.name == other.name:
            return docker_compare(self.version, other.version)
        else:
            return self.name > other.name

