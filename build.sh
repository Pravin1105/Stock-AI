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

# 4. Copy dataset, model, and source code into api/ so Vercel bundles them into the serverless function
mkdir -p api/dataset api/model
cp dataset/train.csv api/dataset/
cp model/tuned_xgboost_model.json api/model/
rm -rf api/src
cp -r src api/src
find api/src -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo "Bundled dataset, model, and src into api/ for serverless availability."
