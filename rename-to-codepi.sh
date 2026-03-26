#!/bin/bash

# Script to rename mypi package to codepi
# Run this from the repository root: bash rename-to-codepi.sh

set -e  # Exit on error

echo "🔄 Starting package rename: mypi → codepi"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -d "mypi" ]; then
    echo -e "${RED}❌ Error: mypi directory not found. Run this script from the repository root.${NC}"
    exit 1
fi

# Step 1: Update pyproject.toml
echo -e "${YELLOW}1️⃣  Updating pyproject.toml...${NC}"
if [ -f "pyproject.toml" ]; then
    sed -i.bak 's/name = "mypi"/name = "codepi"/' pyproject.toml
    sed -i.bak 's/mypi = "mypi\.__main__:main"/codepi = "codepi.__main__:main"/' pyproject.toml
    sed -i.bak 's/mypi\.egg-info/codepi.egg-info/' pyproject.toml
    rm -f pyproject.toml.bak
    echo -e "${GREEN}✓ pyproject.toml updated${NC}"
else
    echo -e "${RED}❌ pyproject.toml not found${NC}"
    exit 1
fi

# Step 2: Update .gitignore
echo -e "${YELLOW}2️⃣  Updating .gitignore...${NC}"
if [ -f ".gitignore" ]; then
    sed -i.bak 's/mypi\.egg-info/codepi.egg-info/' .gitignore
    rm -f .gitignore.bak
    echo -e "${GREEN}✓ .gitignore updated${NC}"
fi

# Step 3: Update import statements in Python files
echo -e "${YELLOW}3️⃣  Updating import statements in Python files...${NC}"
find . -type f -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./venv/*" | while read file; do
    if grep -q "from mypi" "$file" || grep -q "import mypi" "$file"; then
        sed -i.bak 's/from mypi\./from codepi./g' "$file"
        sed -i.bak 's/import mypi\./import codepi./g' "$file"
        sed -i.bak 's/from mypi$/from codepi/g' "$file"
        sed -i.bak 's/import mypi$/import codepi/g' "$file"
        rm -f "$file.bak"
        echo "  ✓ Updated: $file"
    fi
done

# Step 4: Rename the main package directory
echo -e "${YELLOW}4️⃣  Renaming mypi directory to codepi...${NC}"
mv mypi codepi
echo -e "${GREEN}✓ Directory renamed: mypi → codepi${NC}"

# Step 5: Update README.md if it exists
echo -e "${YELLOW}5️⃣  Updating README.md...${NC}"
if [ -f "README.md" ]; then
    sed -i.bak 's/pip install mypi/pip install codepi/g' README.md
    sed -i.bak 's/from mypi\./from codepi./g' README.md
    sed -i.bak 's/import mypi/import codepi/g' README.md
    sed -i.bak 's/^mypi/codepi/g' README.md
    rm -f README.md.bak
    echo -e "${GREEN}✓ README.md updated${NC}"
fi

# Step 6: Update any markdown documentation files
echo -e "${YELLOW}6️⃣  Updating documentation files...${NC}"
find . -type f \( -name "*.md" -o -name "*.rst" \) -not -path "./.git/*" | while read file; do
    if grep -q "mypi" "$file"; then
        sed -i.bak 's/pip install mypi/pip install codepi/g' "$file"
        sed -i.bak 's/from mypi\./from codepi./g' "$file"
        sed -i.bak 's/import mypi/import codepi/g' "$file"
        rm -f "$file.bak"
        echo "  ✓ Updated: $file"
    fi
done

# Step 7: Update GitHub Actions workflows (if present)
echo -e "${YELLOW}7️⃣  Checking for GitHub Actions workflows...${NC}"
if [ -d ".github/workflows" ]; then
    find .github/workflows -type f -name "*.yml" -o -name "*.yaml" | while read file; do
        if grep -q "mypi" "$file"; then
            sed -i.bak 's/mypi/codepi/g' "$file"
            rm -f "$file.bak"
            echo "  ✓ Updated: $file"
        fi
    done
fi

# Step 8: Summary
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Package rename complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "📋 Summary of changes:"
echo "  ✓ pyproject.toml: package name updated"
echo "  ✓ .gitignore: egg-info path updated"
echo "  ✓ All Python files: imports updated"
echo "  ✓ Directory renamed: mypi → codepi"
echo "  ✓ README.md: installation & usage updated"
echo "  ✓ Documentation files: references updated"
echo ""
echo "🚀 Next steps:"
echo "  1. Review the changes: git diff"
echo "  2. Test the package: python -m pytest"
echo "  3. Test imports: python -c 'from codepi import ...'"
echo "  4. Commit the changes: git add -A && git commit -m 'Rename package from mypi to codepi'"
echo ""

