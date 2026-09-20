#!/usr/bin/env bash
set -e

# 1. Build Vite frontend
cd frontend
npm install
npm run build

# 2. Adjust hardcoded localhost to relative /api or custom VITE_API_BASE_URL for production
node -e "
const fs = require('fs');
const dir = 'dist/assets';
if (fs.existsSync(dir)) {
  fs.readdirSync(dir).filter(f => f.endsWith('.js')).forEach(f => {
    const p = dir + '/' + f;
    const content = fs.readFileSync(p, 'utf8');
    fs.writeFileSync(p, content.replace(/http:\/\/127\.0\.0\.1:8000/g, process.env.VITE_API_BASE_URL || ''));
  });
}
"
cd ..

# 3. Populate root public/ directory so Vercel CDN serves static assets directly
rm -rf public
mkdir -p public
cp -r frontend/dist/* public/
echo "Static frontend ready in public/ for CDN distribution."

# 4. Copy requirements, dataset, model, and source code into api/ so Vercel bundles them into the serverless function
cp requirements.txt api/requirements.txt
mkdir -p api/dataset api/model
cp dataset/train.csv api/dataset/
cp model/tuned_xgboost_model.json api/model/
rm -rf api/src
cp -r src api/src
find api/src -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo "Bundled requirements, dataset, model, and src into api/ for serverless availability."

# 5. Clean up heavy frontend node_modules and dataset working cache (frontend/dist is only ~200KB and preserved)
rm -rf frontend/node_modules
rm -rf dataset/working
echo "Pruned frontend/node_modules and build caches to optimize bundle size."

# 6. Replace heavy scipy with a minimal stub to stay under Vercel's 500 MB bundle limit.
#    uv already installed the real scipy (~150-200 MB on Linux) as a transitive dep of xgboost.
#    Our code only uses xgb.Booster / xgb.DMatrix with pandas DataFrames (inference only),
#    so the full scipy is never exercised. The stub satisfies xgboost's top-level
#    `import scipy.sparse` without the compiled linear algebra libraries.
SITE_PACKAGES=$(python3 -c "import site; print(site.getsitepackages()[0])" 2>/dev/null || echo "")
if [ -z "$SITE_PACKAGES" ] || [ ! -d "$SITE_PACKAGES" ]; then
    # Fallback: locate scipy and derive site-packages from it
    SITE_PACKAGES=$(python3 -c "import scipy, os; print(os.path.dirname(os.path.dirname(scipy.__file__)))" 2>/dev/null || echo "")
fi
if [ -z "$SITE_PACKAGES" ] || [ ! -d "$SITE_PACKAGES" ]; then
    # Vercel-specific fallback
    for d in /vercel/path0/.vercel/python/.venv/lib/python*/site-packages; do
        [ -d "$d" ] && SITE_PACKAGES="$d" && break
    done
fi

if [ -n "$SITE_PACKAGES" ] && [ -d "$SITE_PACKAGES/scipy" ]; then
    SCIPY_SIZE=$(du -sm "$SITE_PACKAGES/scipy" 2>/dev/null | cut -f1)
    echo "Replacing scipy (${SCIPY_SIZE:-?} MB) with minimal stub..."

    rm -rf "$SITE_PACKAGES/scipy" "$SITE_PACKAGES/scipy.libs" "$SITE_PACKAGES"/scipy-*.dist-info

    # -- scipy/__init__.py --
    mkdir -p "$SITE_PACKAGES/scipy/sparse"
    cat > "$SITE_PACKAGES/scipy/__init__.py" << 'STUBEOF'
"""Minimal scipy stub – satisfies xgboost import without the full package."""
from . import sparse
STUBEOF

    # -- scipy/sparse/__init__.py --
    cat > "$SITE_PACKAGES/scipy/sparse/__init__.py" << 'STUBEOF'
"""Stub scipy.sparse providing the classes/functions xgboost references."""

class csr_matrix:
    pass

class csc_matrix:
    pass

class coo_matrix:
    pass

csr_array = csr_matrix
csc_array = csc_matrix
coo_array = coo_matrix

def issparse(x):
    return False

def isspmatrix(x):
    return False

def isspmatrix_csr(x):
    return False

def isspmatrix_csc(x):
    return False

def vstack(*a, **kw):
    raise NotImplementedError("scipy.sparse.vstack stub – not available in production")
STUBEOF

    # -- scipy/special/__init__.py  (xgboost/sklearn.py imports softmax/expit) --
    mkdir -p "$SITE_PACKAGES/scipy/special"
    cat > "$SITE_PACKAGES/scipy/special/__init__.py" << 'STUBEOF'
"""Stub scipy.special – only needed if xgboost sklearn wrapper is loaded."""
def softmax(x, axis=None):
    raise NotImplementedError("scipy.special.softmax stub")
def expit(x):
    raise NotImplementedError("scipy.special.expit stub")
STUBEOF

    echo "scipy stub installed successfully (saved ~${SCIPY_SIZE:-150} MB)."
else
    echo "Warning: scipy not found at $SITE_PACKAGES/scipy – skipping stub replacement."
fi

# Also place the scipy stub directly into api/_vendor/scipy and _vendor/scipy
# so regardless of which python runtime path resolution is used, 'import scipy' succeeds
for target in "api/_vendor/scipy" "_vendor/scipy"; do
    mkdir -p "$target/sparse" "$target/special"
    cat > "$target/__init__.py" << 'STUBEOF'
"""Minimal scipy stub – satisfies xgboost import without the full package."""
from . import sparse
STUBEOF
    cat > "$target/sparse/__init__.py" << 'STUBEOF'
class csr_matrix:
    pass
class csc_matrix:
    pass
class coo_matrix:
    pass
csr_array = csr_matrix
csc_array = csc_matrix
coo_array = coo_matrix
def issparse(x):
    return False
def isspmatrix(x):
    return False
def isspmatrix_csr(x):
    return False
def isspmatrix_csc(x):
    return False
def vstack(*a, **kw):
    return None
STUBEOF
    cat > "$target/special/__init__.py" << 'STUBEOF'
def softmax(x, axis=None):
    return None
def expit(x):
    return None
STUBEOF
done
echo "Vendored in-bundle scipy stub in api/_vendor/scipy and _vendor/scipy."

# 7. Strip test, doc, and benchmark suites from site-packages to reclaim another 30-40 MB
if [ -n "$SITE_PACKAGES" ] && [ -d "$SITE_PACKAGES" ]; then
    echo "Stripping test suites and docs from site-packages..."
    find "$SITE_PACKAGES" -type d \( -name "tests" -o -name "test" -o -name "testing" -o -name "docs" -o -name "examples" -o -name "benchmarks" \) -exec rm -rf {} + 2>/dev/null || true
    echo "Pruned test suites and docs from site-packages."
fi
