#!/usr/bin/env bash

# Script to (selectively) save/load multiple Docker images to/from a directory.
# Run ./save-load-docker-images.sh for help.

set -e

directory=$PWD
filter=""
compress=0

while getopts ":f:d::zD" opt ${@:2}; do
  case $opt in
    f)
      filter=$OPTARG
      ;;
    d)
      directory=$OPTARG
      ;;
    D)
      DRY_RUN=1
      ;;
    z)
      compress=1
      ;;
    F)
      filename=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      ;;
  esac
done

help () {
    echo
    echo "\
Usage: save [-f filter] [-d dir]   Save all Docker images to a directory
       load [-f filter] [-d dir]   Find all saved images (.tar) in a directory then import to Docker

       -d dir                     Directory to save/load images to/from (defaults to \$PWD)
       -D                         Dry run to not actually do anything just say what would be done.
       -f filter                  Filter images by their name (inclusive)
       -F /path/to/file           Use a text file with image names to save
       -z                         Use gzip to compress/uncompress archives (saved/loaded as *.tar.gz)
"
    echo
}

get-image-field() {
  local imageId=$1
  local field=$2
  : ${imageId:? required}
  : ${field:? required}

  docker images --no-trunc | sed -n "/${imageId}/s/  */ /gp" | cut -d " " -f $field
}

get-image-name() {
  get-image-field $1 1
}

get-image-tag() {
  get-image-field $1 2
}

get-image-id-from-name() {
  docker images $1 --format '{{.ID}}'
}

save-all-images() {
  local ids=$(docker images --no-trunc -q)
  local name safename tag

  for id in $ids; do
    name=$(get-image-name $id)
    tag=$(get-image-tag $id)

    # Apply filter (if any)
    if [[ ! -z "$filter" ]] && [[ ! "$name:$tag" =~ "$filter" ]];then
      continue
    fi

    # Ignore stale images (tag == <none>)
    if [[ "$tag" = "<none>" ]]; then
      continue
    fi

    if [[ $name =~ / ]]; then
       dir=${name%/*}
       mkdir -p "$directory/$dir"
    fi

    echo "Saving $name:$tag ..."
    [[ $compress -eq 0 ]] && file_extension="tar" || file_extension="tar.gz"
    if [ ! -z "${DRY_RUN}" ]; then
        echo "dry run: docker save to $directory/$name.$tag.$file_extension"
        continue
    fi
    if [[ $compress -eq 0 ]]; then
       docker save -o "$directory/$name.$tag.$file_extension" $name:$tag
    else
      docker save $name:$tag | gzip > "$directory/$name.$tag.$file_extension"
    fi
  done
}

load-all-images() {
  local name safename noextension tag

  if [[ $compress -eq 0 ]]; then
    file_extension="tar"
  else
    file_extension="tar.gz"
  fi
  for image in $(find "$directory" -name \*.$file_extension); do
    if [[ ! -z "$filter" ]] && [[ ! "$image" =~ "$filter" ]];then
      continue
    fi
    echo "Loading $image ..."
    if [ ! -z "${DRY_RUN}" ]; then
        echo "dry run: docker load from $directory/$name.$tag.$file_extension"
        continue
    fi
    docker load -i $image
  done
}

get-ids-from-file() {
    local ids images image
    images==$(cat $filename)
    for image in $images; do
        id=$(get-image-id-from-name $image)
        ids="$ids $id"
    done
    echo $ids
}

case $1 in
    save)
      save-all-images
    ;;
    load)
      load-all-images
    ;;
    *)
        help
    ;;
esac

exit 0
