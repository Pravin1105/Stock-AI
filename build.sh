#!/usr/bin/env bash
set -e

cd frontend
npm install
npm run build

# Adjust hardcoded localhost to relative /api or custom VITE_API_BASE_URL for production
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
