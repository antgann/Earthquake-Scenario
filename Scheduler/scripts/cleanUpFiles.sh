#!/bin/bash

# clean up user generated files

rm -f `dirname $0`/../BuiltEvents/*

find /app/eew/EEWScenario/Scheduler/logs/ -type f -name "*.log" -mtime +30 | xargs tar -czvPf ../logs/archive/EEWScenarioLogArchive_$(date +%F).tar.gz

find /app/eew/EEWScenario/Scheduler/logs/ -type f -name "*.log" -mtime +30 -delete



