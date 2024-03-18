#!/bin/bash

if [[ $CASBOT_DIR == "" ]]; then
    CASBOT_DIR=.
fi

docker-compose -f $CASBOT_DIR/docker-compose.yml -p cas up --build
