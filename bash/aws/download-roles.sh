#!/usr/bin/env bash
ROLE_ARNS=$(aws iam list-roles --query "Roles[].Arn" --output text)
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
mkdir -p aws-iam/
for ARN in ${ROLE_ARNS}; do
    if ! echo $ARN | grep $AWS_ACCOUNT; then
        continue
    fi
    _DIR=$(dirname ${ARN})
    _NAME=$(basename ${ARN})
    mkdir -p aws-iam/${_DIR}
    echo "Getting role ${_NAME}"
    aws iam get-role --role-name ${_NAME} > "aws-iam/${ARN}.json"
    aws iam list-role-policies --role-name ${_NAME} > "aws-iam/${ARN}-policies.json"
done