#!/usr/bin/env bash

#TODO: refactor as needed

rm -rf docs/* 
sphinx-apidoc -f -o source darwin darwin/future
sphinx-build -b html source/ docs/ -W