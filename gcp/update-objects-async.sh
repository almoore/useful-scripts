#!/usr/bin/env bash
BUCKET=${BUCKET}
OBJ_PATH=${OBJ_PATH}
KMS_KEY=$(gcloud storage buckets describe ${BUCKET} --format="yaml(encryption)"|yq -r .encryption.defaultKmsKeyName)
OLD_KMS_KEY=null
OBJECT_JSON=$(gcloud storage objects list ${BUCKET}/${OBJ_PATH}/* \
  --filter="kmsKeyName:${OLD_KMS_KEY}" \
  --format=json \
)
OBJECT_NAMES=$(echo $OBJECT_JSON| jq -r '.[].name')

open_sem(){
    mkfifo pipe-$$
    exec 3<>pipe-$$
    rm pipe-$$
    local i=$1
    for((;i>0;i--)); do
        printf %s 000 >&3
    done
}

# run the given command asynchronously and pop/push tokens
run_with_lock(){
    local x
    # this read waits until there is something to read
    read -u 3 -n 3 x && ((0==x)) || exit $x
    (
     ( "$@"; )
    # push the return code of the command to the semaphore
    printf '%.3d' $? >&3
    )&
}
pids=()

N=20
open_sem $N
for OBJECT_NAME in $OBJECT_NAMES; do
  # OBJECT_KEY=$(gcloud storage objects describe ${BUCKET}/${OBJECT_NAME} --format="yaml(kmsKeyName)"|yq -r .kmsKeyName | sed 's#/cryptoKeyVersions/.*$##')
  OBJECT_KEY=$(echo $OBJECT_JSON | jq -r '.[]|select(.name=="'${OBJECT_NAME}'")|.kmsKeyName')
  if [ "$OBJECT_KEY" != $KMS_KEY ]; then
    if [ "$OBJECT_KEY" != "${OLD_KMS_KEY}" ]; then
      DECRYPTION_KEY_ARG="--decryption-keys=$OBJECT_KEY"
    fi
    CMD="gcloud storage objects update ${BUCKET}/${OBJECT_NAME} --encryption-key=$KMS_KEY $DECRYPTION_KEY_ARG"
    echo $CMD
    run_with_lock $CMD
    pids+=( $! )
  fi
done

for pid in ${pids[@]}; do
    wait $pid
done
