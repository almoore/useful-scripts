import json
import yaml
import colorize
import logging


class KubeBackup():
    logger = logging.getLogger(__name__)

    GLOBAL_TYPES = [
        "node",
        "apiservice",
        "clusterrole",
        "clusterrolebinding",
        "podsecuritypolicy",
        "storageclass",
        "persistentvolume",
        "customresourcedefinition",
        "mutatingwebhookconfiguration",
        "validatingwebhookconfiguration",
        "priorityclass"
    ]

    TYPES = [
        "serviceaccount",
        "secret",
        "deployment",
        "daemonset",
        "statefulset",
        "configmap",
        "cronjob",
        "ingress",
        "networkpolicy",
        "persistentvolumeclaim",
        "rolebinding",
        "service",
        "pod",
        "endpoints",
        "resourcequota",
        "horizontalpodautoscaler",
    ]

    SKIP_POD_OWNERS = [
        "DaemonSet",
        "ReplicaSet",
        "Job",
        "StatefulSet"
    ]

    def perform_backup(self, options={}):
        logger.info("Args: {}".format(options))

        if not options["repo_url"] or options["repo_url"] == '':
            raise OptionParser::MissingArgument, "Git repo-url is required, please specify --repo-url or GIT_REPO_URL"

        global_types = combine_types(GLOBAL_TYPES.dup,
                                     extras: options["extra_global_resources"],
                                     exclude: options["skip_global_resources"],
                                     only: options["global_resources"]
        )
        if global_types != GLOBAL_TYPES:
            logger.info("Global Types: #{}".format(LogUtil.dump(global_types)))

        types = combine_types(TYPES.dup,
                              extras: options["extra_resources"],
                              exclude: options["skip_resources"],
                              only: options["resources"]
        )
        if types != TYPES:
            logger.info("Types: {}".format(LogUtil.dump(types)))

        skip_patterns = (options["skip_objects"] or "").split(",").map( & : strip)
        global_skip_patterns = skip_patterns.select { | pattern | pattern.scan("/").size == 1}
        skip_patterns -= global_skip_patterns

        if global_skip_patterns.size > 0:
            logger.info("Global Skip Patterns: {}".format(LogUtil.dump(global_skip_patterns)))
        if skip_patterns.size > 0:
            logger.info("Skip Patterns: {}".format(LogUtil.dump(skip_patterns)))

        skip_namespaces = options["skip_namespaces"] ? options["skip_namespaces"].split(","): []
        only_namespaces = options["only_namespaces"] ? options["only_namespaces"].split(","): None

        writter = Writter.new(options)
        writter.init_repo!

        for _type in global_types:
            resources = kubectl("get", _type)
            print("Got {size} {kind}s".format(size=len(resources["items"]), kind=_type))

            for item in resources["items"]:
                if skip_object?(item, global_skip_patterns):
                   name = item.dig("metadata", "name")
                   logger.info("skip resource {}".format(item["kind"]))
                   next

                clean_resource!(item)
                writter.write_res(item)

        for _type in types:
            resources = kubectl("get", _type, "all-namespaces" = > None)
            print("Got {size} {kind}s".format(size=len(resources["items"]), kind=_type))

            if not resources["items"]:
                logger.error("Can not get resource {kind}".format(kind=_type))
                print(json.dumps(resources, indent=2))
                exit(1)

            for item in resources["items"]:

                if item["kind"] == "Secret" && item["type"] == "kubernetes.io/service-account-token":
                    next

                # skip pods with ownerReferences (means created by deployment, cronjob, daemonset)
                if item["kind"] == "Pod" & & item.dig("metadata", "ownerReferences"):
                   if item["metadata"]["ownerReferences"].size > 1:
                       print(yaml.dump(item, default_flow_style=False, canonical=False))
                       raise "many ownerReferences"

                   ref = item["metadata"]["ownerReferences"].first
                   if SKIP_POD_OWNERS.include?(ref["kind"]):
                       next

                if item["kind"] == "Endpoints":
                    if item["subsets"] & & item["subsets"][0]:
                        if addresses = item["subsets"][0]["addresses"] or addresses = item["subsets"][0]["notReadyAddresses"]:
                            if addresses[0] & & addresses[0]["targetRef"] && addresses[0]["targetRef"]["kind"] == "Pod":
                                # skip endpoints created by services
                                next

                namespace = item.dig("metadata", "namespace")

                if namespace in skip_namespaces:
                    name = item.dig("metadata", "name")
                    logger.info("skip resource {namespace}/{kind}/{name} by namespace filter".format(namespace=namespace,kind=item["kind"], name=name))
                next

                if only_namespaces && not namespace in only_namespaces:
                    name = item.dig("metadata", "name")
                    logger.info("skip resource {namespace}/{kind}/{name} by namespace filter".format(namespace=namespace,kind=item["kind"],name=name))
                next

                if skip_object(item, skip_patterns):
                    name = item.dig("metadata", "name")
                    logger.info("skip resource {namespace}/{kind}/{name}".format(namespace=namespace,kind=item["kind"],name=name))
                next

                clean_resource(item)
                return writter.write_ns_res(item)

        Plugins::Grafana.new(writter).run

        writter.print_changed_files

    def kubectl(self, command, resource, options={}):
        options["o"] or= 'json'

        args = options.to_a.map do | key, value|
        key = key.to_s
        key = "-#{key.size > 1 ? "-" : ""}#{key}"

            if not value:
                [key]
            else:
                [key, "#{value}"]
                end.flatten

        res = cmd("kubectl", command, resource, *args, ENV.to_h)

        if not res["success"]:
            logger.error(res["stderr"])

        if res["stdout"] & & res["stdout"].size > 0:
            return json.loads(res["stdout"])
        else:
            return {"items": []} # dummy

    def clean_resource(resource):
        del_metadata_keys = [
            "creationTimestamp",
            "selfLink",
            "uid",
            "resourceVersion",
            "generation",
        ]
        del_annotations_keys = [
            "kubectl.kubernetes.io/last-applied-configuration",
            "control-plane.alpha.kubernetes.io/leader",
            "deployment.kubernetes.io/revision",
            "cattle.io/creator",
            "field.cattle.io/creatorId",
        ]
        if "status" in resource.keys():
            resource.__delitem__("status")
        
        if resource.get("metadata"):
            for key in del_metadata_keys:
                if key in resource["metadata"].keys():
                    resource["metadata"].__delitem__(key)
        
            if resource["metadata"].get("annotations"):
                for key in del_annotations_keys:
                    if key in resource["metadata"]["annotations"].keys():
                        resource["metadata"]["annotations"].__delitem__(key)
        
                if resource["metadata"]["annotations"] == {}:
                    resource["metadata"].__delitem__("annotations")
        
            if resource["metadata"].get("namespace") == '':
                resource["metadata"].__delitem__("namespace")
        
            if resource["metadata"] == {}:
                resource.__delitem__("metadata")
        
        if resource["kind"] == "Service" and resource.get("spec"):
            if resource["spec"].get("clusterIP") is not None:
                resource["spec"].__delitem__("clusterIP")
            if resource["spec"] == {}:
                resource.__delitem__("spec")
        return resource



    def combine_types(self, types, extras: , exclude:, only:):
       if only:
            return only.downcase.split(",").map(&: strip).map(&:to_sym)

        if extras:
            extras = extras.downcase.split(",").map(&: strip).map(&:to_sym)
            types.push(*extras)

        if exclude:
            exclude = exclude.downcase.split(",").map(&: strip).map(&:to_sym)
            types.delete_if {|r | exclude.include?(r) }:

        return types

    def skip_object?(self, item, patterns):
        return False if len(patterns) == 0:

        ns = item.dig("metadata", "namespace")
        ns = None if ns == '':

        object_parts = [ns, item["kind"], item.dig("metadata", "name")].compact

        for pattern in patterns:
            pattern = pattern.downcase

            if pattern == object_parts.join("/").lower():
               return True

            pattern_parts = pattern.split("/")
            mismatch = False
            for  in object_parts.each_with_index:
                if pattern_parts[index] == "*" or part.downcase == pattern_parts[index]:
                    # good
                    continue
                else:
                    mismatch = True
            if mismatch:
                return True 

        return False

    def push_changes(self, options):
        writter = Writter.new(options)

        changes_list = writter.get_changes

        if changes_list:
            changes_lines = changes_list.split("\n")
            namespaces = []
            resources = []

            prefix = options["git_prefix"] ? options["git_prefix"].sub( /\/$/, '') + "/" : False

            for line in changes_lines:
                line = line.strip.gsub('"', '')
                info = line.match(/^(?< prefix>.+?)\s+(?<file>.+)$/)
                info["file"].sub(prefix, '') if prefix
                file_parts = info["file"].sub( /\.yaml$/, '').split("/")

                if file_parts[0] != "_global_":
                    namespaces << file_parts[0]
                    resources << file_parts[1]
                    namespaces = list(set(namespaces))
                    resource = list(set(resources))

            message = "Updated {res} in namespace{plural} {ns} item{pural2}".format(
                    res=len(resources) > 0 ? ",".join(resources) : None,
                    plural=namespaces.size > 0 ? "s" : "",
                    ns=",".join(namespaces): None,
                    plural2=len(changes_lines) > 1 ? "s" : ""
            )

           return  writter.push_changes(message)


