#!/usr/bin/env bash
POLICY_ARNS=$(aws iam list-policies --query "Policies[].Arn" --output text)
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
mkdir -p aws-iam/arn:aws:iam::aws:policy
for ARN in ${POLICY_ARNS}; do
    if ! echo $ARN | grep $AWS_ACCOUNT; then
        continue
    fi
    _DIR=$(dirname ${ARN})
    mkdir -p aws-iam/${_DIR}
    echo -n "Getting policy ${ARN} "
    V=$(aws iam get-policy --policy-arn ${ARN} --query Policy.DefaultVersionId --output text)
    echo $V
    aws iam get-policy-version --policy-arn ${ARN} --version-id $V --query PolicyVersion.Document > "aws-iam/${ARN}.json"
done