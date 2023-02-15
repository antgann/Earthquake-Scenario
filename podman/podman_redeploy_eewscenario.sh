#!/bin/bash

podman stop eewscenario

podman rm eewscenario

podman build -t eewscenario-dev .

podman run -dt --name eewscenario --pod scenariopod eewscenario-dev:latest



