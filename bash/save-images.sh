get-image-id-from-name() {
  docker images $1 --format '{{.ID}}'
}

DIR=/usr/local/opt/dockersave
for i in $(cat /tmp/docker-save.txt); do
    ID=$(docker images $i --format '{{.ID}}');
    name=$(echo $i|awk -F':' '{print $1}'|sed 's|[\/]|_|g')
    tag=$(echo $i|awk -F':' '{print $2}')
    if [ ! -f $DIR/${name}_${tag}.tar ]; then
        echo "Saving: $i => $DIR/${name}_${tag}.tar"
        docker save $ID -o /usr/local/opt/dockersave/${name}_${tag}.tar
    else
        echo "Image already found $DIR/${name}_${tag}.tar"
    fi
done
