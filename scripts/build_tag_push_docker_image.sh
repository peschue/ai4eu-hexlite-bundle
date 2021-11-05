#!/bin/bash

# execute this in the root of the repo!

LOCAL_IMAGE_TAG=hexlite-bundle:latest
REPO_IMAGE_TAG=cicd.ai4eu-dev.eu:7444/reasoners/hexlite-bundle:1.0

docker build . -f Dockerfile -t $LOCAL_IMAGE_TAG -t $REPO_IMAGE_TAG
docker push $REPO_IMAGE_TAG