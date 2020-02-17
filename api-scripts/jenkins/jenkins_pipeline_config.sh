#!/bin/bash

debug=0
PROJECT_NAME="SALT"
SERVER="http://p-gp2-devopsjenkins-1.imovetv.com:8080"
BRANCHES="dev prod beta qa"

usage() {
    echo "Usage: $0 [options] REPO_NAME"
    echo "This script is meant to create a simple pipeline config file."
    echo "Options:"
    echo "         --debug     turn on debug output"
    echo "    -b | --branches  specify the branch config (default='dev prod beta qa')"
    echo "    -n | --plan-name specify the jenkins plan name"
    echo "    -p | --project   specify a project (default=salt)"
    echo "    -s | --server    specify the jenkins server url to use"
    echo ""
    echo "    -h | --help      print this message"
}

while [ -n "${1}" ]
do
    case "${1}" in
        --debug)
            debug=1
            ;;
        -p | --project)
            shift
            PROJECT_NAME="${1}"
            ;;
        -n | --plan-name)
            shift
            PLAN_NAME="${1}"
            ;;
        -b | --branches)
            shift
            BRANCHES="${1}"
            ;;
        -s | --server)
            shift
            SERVER="${1}"
            ;;
        -h | --help)
            usage
            exit
            ;;
        *)
            if [ -z "$_REPO_NAME" ]; then
                _REPO_NAME="${1##*/}"
            else
                usage
                exit
            fi
            ;;
    esac
    shift
done

if [ "${debug}" -ne 0 ]; then
    set -x
fi

if [ ! -z "$_REPO_NAME" ]; then
    if [ -z "${PLAN_NAME}" ]; then
        PLAN_NAME="${_REPO_NAME}-state"
    fi

    REPO_URL="ssh://git@p-bitbucket.imovetv.com:7999/${PROJECT_NAME}/${_REPO_NAME}.git"
    BROWSE_URL="http://p-bitbucket.imovetv.com/projects/${PROJECT_NAME}/repos/${_REPO_NAME}/browse"
    TMPFILE=$(mktemp /tmp/job.conf.XXX)
    echo "Created $TMPFILE"
cat <<EOF > $TMPFILE
<?xml version='1.0' encoding='UTF-8'?>
<org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject plugin="workflow-multibranch@2.12">
  <actions/>
  <description></description>
  <properties>
    <org.jenkinsci.plugins.pipeline.modeldefinition.config.FolderConfig plugin="pipeline-model-definition@1.0.1">
      <dockerLabel></dockerLabel>
      <registry plugin="docker-commons@1.6"/>
    </org.jenkinsci.plugins.pipeline.modeldefinition.config.FolderConfig>
  </properties>
  <folderViews class="jenkins.branch.MultiBranchProjectViewHolder" plugin="branch-api@2.0.4">
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
  </folderViews>
  <healthMetrics>
    <com.cloudbees.hudson.plugins.folder.health.WorstChildHealthMetric plugin="cloudbees-folder@5.17">
      <nonRecursive>false</nonRecursive>
    </com.cloudbees.hudson.plugins.folder.health.WorstChildHealthMetric>
  </healthMetrics>
  <icon class="jenkins.branch.MetadataActionFolderIcon" plugin="branch-api@2.0.4">
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
  </icon>
  <orphanedItemStrategy class="com.cloudbees.hudson.plugins.folder.computed.DefaultOrphanedItemStrategy" plugin="cloudbees-folder@5.17">
    <pruneDeadBranches>true</pruneDeadBranches>
    <daysToKeep>0</daysToKeep>
    <numToKeep>0</numToKeep>
  </orphanedItemStrategy>
  <triggers>
    <com.cloudbees.hudson.plugins.folder.computed.PeriodicFolderTrigger plugin="cloudbees-folder@5.17">
      <spec>H * * * *</spec>
      <interval>3600000</interval>
    </com.cloudbees.hudson.plugins.folder.computed.PeriodicFolderTrigger>
  </triggers>
  <sources class="jenkins.branch.MultiBranchProject\$BranchSourceList" plugin="branch-api@2.0.4">
    <data>
      <jenkins.branch.BranchSource>
        <source class="jenkins.plugins.git.GitSCMSource" plugin="git@3.0.5">
          <id>12b607b9-2826-442e-b00a-566b5c9652f0</id>
          <remote>${REPO_URL}</remote>
          <includes>${BRANCHES}</includes>
          <excludes></excludes>
          <ignoreOnPushNotifications>false</ignoreOnPushNotifications>
          <browser class="hudson.plugins.git.browser.Stash">
            <url>${BROWSE_URL}</url>
          </browser>
        </source>
        <strategy class="jenkins.branch.DefaultBranchPropertyStrategy">
          <properties class="empty-list"/>
        </strategy>
      </jenkins.branch.BranchSource>
    </data>
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
  </sources>
  <factory class="org.jenkinsci.plugins.workflow.multibranch.WorkflowBranchProjectFactory">
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
  </factory>
</org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject>
EOF

USERNAME="devopsjenkins@echostar.com"
PASSWORD="xlontestit"
CRUMB=$(curl --user ${USERNAME}:${PASSWORD} \
    $SERVER/crumbIssuer/api/xml?xpath=concat\(//crumbRequestField,%22:%22,//crumb\))

curl -f -X POST \
     -H "Content-Type:application/xml" \
     -H 'accept: application/json' \
     -H "${CRUMB}" \
     -d @$TMPFILE \
     $SERVER/createItem?name=${PLAN_NAME} -u ${USERNAME}:${PASSWORD}

EXIT_CODE=$?
cat $TMPFILE
rm $TMPFILE

exit $EXIT_CODE
else
    usage
fi
