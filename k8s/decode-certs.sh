#!/usr/bin/env bash
# Find every kubernetes.io/tls Secret manifest under the current directory and
# print the validity window of its tls.crt via openssl x509.
CERTSECRETS=$(grep -r kubernetes.io/tls -l )
for s_cert in $CERTSECRETS; do
echo $s_cert
yq '.data["tls.crt"]' $s_cert -r | base64 -d | openssl x509 -noout -text | grep Validity -A 3 --color=auto
done