#!/usr/bin/env bash
trap_caught()
{
    rm $TMPDIR
}
trap trap_caught SIGINT SIGTERM

usage() {
cat << EOF
USAGE: ${0##*/} [options]
  options:
  -p | --prefix PREFIX               Where to put executables (default: /usr/local/bin)
  -k | --kube-version KUBE_VERSION   The kubectl version to use or download
  -c | --cluster AWS_CLUSTER_NAME    The eks cluster name to query aws.
  -vvv | --debug
EOF
}

DEBUG=0

while [ "$1" != "" ] ; do
    case $1 in
        -p | --prefix )
            shift
            PREFIX="${1}"
            ;;
        -k | --kube-version )
            shift
            KUBE_VERSION="${1}"
            ;;
        -c | --cluster )
            shift
            AWS_CLUSTER_NAME="${1}"
        ;;
        --kubeconfig )
            shift
            export KUBECONFIG="${1}"
            ;;
        -vvv | --debug )
            DEBUG=1
            ;;
        -h | --help )
            usage
            exit 0
            ;;
        * )
            CMD+=( "${1}" )
            ;;
    esac
shift
done

KUBE_VERSION="${KUBE_VERSION:-1.13.0}"
TMPDIR=$(mktemp -d)
PREFIX="${PREFIX:-/usr/local/bin}"
AWS_CLUSTER_NAME="${AWS_CLUSTER_NAME:-""}"
AWS_REGION="${AWS_REGION:-$(aws configure get region)}"

print_out() {
    echo -e '\E[32m'"$@"'\E[0m'
}

set -e

if [ "$DEBUG" -eq "1" ]; then
    set -x
fi

if [ ! -d "$PREFIX" ]; then
    mkdir -p "$PREFIX"
fi

if ! which kubectl 2>&1 > /dev/null ; then
    # Add kubectl and clean up
    curl -L https://storage.googleapis.com/kubernetes-release/release/v$KUBE_VERSION/bin/linux/amd64/kubectl \
     -o ${TMPDIR}/kubectl && \
    chmod +x ${TMPDIR}/kubectl
    mv  ${TMPDIR}/kubectl "${PREFIX}/"
    kubectl version --client
fi

if ! which aws-iam-authenticator 2>&1 > /dev/null ; then
    # Get aws-iam-authenticator
    curl -L -o ${TMPDIR}/aws-iam-authenticator\
         https://amazon-eks.s3-us-west-2.amazonaws.com/1.11.5/2018-12-06/bin/linux/amd64/aws-iam-authenticator
    chmod +x ${TMPDIR}/aws-iam-authenticator
    mv ${TMPDIR}/aws-iam-authenticator "${PREFIX}/"
fi

if [ -z "${AWS_CLUSTER_NAME}" ]; then
  print_out "Please supply an aws cluster name from eks"
  usage
  exit 1
fi

if ! which aws 2>&1 > /dev/null;  then
    TMP=$(mktemp)
    print_out "Installing awscli"
    pip install "awscli>=1.16.0" > $TMP || $(cat $TMP && rm $TMP && exit 1)
    print_out "Configure the awscli and then run:"
    print_out "   aws eks update-kubeconfig --name ${AWS_CLUSTER_NAME} --region ${AWS_REGION}"
    rm $TMP
else
    aws eks update-kubeconfig --name ${AWS_CLUSTER_NAME} --region ${AWS_REGION}
fi
