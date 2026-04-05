#!/bin/bash

# Updated for macOS compatibility
SEARCH="mypi"
REPLACE="codepi"

# The '' after -i tells macOS sed not to create a backup file
find . -type f -name "*.py" -exec sed -i '' "s/$SEARCH/$REPLACE/g" {} +

echo "Replacement complete in all .py files."
