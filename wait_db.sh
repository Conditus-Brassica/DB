#!bin/sh

until [ "`docker inspect -f {{.State.Running}} CONTAINERNAME`"=="true" ]; do
    sleep 0.1;
done;