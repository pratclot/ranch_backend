#!/bin/sh

set -e

source ./venv/bin/activate

hypercorn serious_quartz:app --error-log - --access-log -

