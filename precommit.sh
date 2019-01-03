#!/bin/bash

set -xeufo pipefail

python3 -m black -l 80 .
python3 -m pytest
