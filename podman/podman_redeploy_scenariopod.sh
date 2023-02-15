#!/bin/bash

podman pod stop scenariopod

podman pod rm scenariopod

podman pod create -n scenariopod -p 8080:8000/tcp



