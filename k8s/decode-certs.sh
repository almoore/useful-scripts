
CERTSECRETS=$(grep -r kubernetes.io/tls -l )
for s_cert in $CERTSECRETS; do
echo $s_cert
yq '.data["tls.crt"]' $s_cert -r | base64 -d | openssl x509 -noout -text | grep Validity -A 3 --color=auto
done