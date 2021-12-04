#! /usr/bin/env bash

inputname=`basename $1`
docker run -v `realpath $2`:/out -v `realpath $1`:/usr/src/app/${inputname} nbr23/watchmap watchmap -i /usr/src/app/${inputname} -o /out