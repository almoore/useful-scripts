#!/usr/bin/env bash
BUCKET=${BUCKET}
OBJ_PATH=${OBJ_PATH}
OLD_KMS_KEY=null
KMS_KEY=$(gcloud storage buckets describe ${BUCKET} --format="yaml(encryption)"|yq -r .encryption.defaultKmsKeyName)
OBJECTS=$(gsutil ls ${BUCKET}/${OBJ_PATH}/)
OBJECT_IDS=$(gcloud storage objects list ${BUCKET}/${OBJ_PATH}/* \
  --filter="kmsKeyName:${OLD_KMS_KEY}" \
  --format="value(id)"
)
for OBJECT_NAME in $OBJECTS; do
  echo $OBJECT_NAME
  OBJECT_KEY=$(gcloud storage objects describe $OBJECT_NAME --format="yaml(kmsKeyName)"|yq -r .kmsKeyName | sed 's#/cryptoKeyVersions/.*$##')
  echo $OBJECT_KEY
  if [ "$OBJECT_KEY" != $KMS_KEY ]; then
    if [ "$OBJECT_KEY" != "${OLD_KMS_KEY}" ]; then
      DECRYPTION_KEY_ARG="--decryption-keys=$OBJECT_KEY"
    fi
    CMD="gcloud storage objects update $OBJECT_NAME --encryption-key=$KMS_KEY $DECRYPTION_KEY_ARG"
    echo $CMD
    eval $CMD
  fi
done
