# Frontend Troubleshooting Guide

## Common Issues and Solutions

### 1. **ESLint Configuration Error**
**Fixed:** Replaced `eslint.config.js` with `.eslintrc.cjs` for better compatibility.

### 2. **Module Not Found Errors**

If you see errors like "Cannot find module", run:
```bash
npm install
```

### 3. **Port Already in Use**

If port 3000 is busy, Vite will automatically suggest another port. Or modify `vite.config.js`:
```js
server: {
  port: 3001, // Change to any available port
}
```

### 4. **CORS Errors**

Make sure your backend has CORS enabled. Add to `app/main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5. **API Connection Issues**

Check that:
- Backend is running on `http://localhost:8000`
- `.env` file exists with: `VITE_API_URL=http://localhost:8000`
- No firewall blocking the connection

### 6. **Blank Page / White Screen**

Open browser console (F12) and check for errors. Common fixes:
- Clear browser cache (Ctrl+Shift+Delete)
- Hard reload (Ctrl+Shift+R)
- Check if all dependencies installed: `npm install`

### 7. **Styling Not Applied**

If Tailwind CSS isn't working:
```bash
# Reinstall Tailwind
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### 8. **Hot Reload Not Working**

Restart the dev server:
```bash
# Stop with Ctrl+C, then:
npm run dev
```

## Quick Fixes

### Reset Everything
```bash
# Delete node_modules and reinstall
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
npm install
npm run dev
```

### Check for Errors
```bash
# Run linter
npm run lint

# Build to check for errors
npm run build
```

## Verified Working Configuration

✅ React 18.2.0
✅ Vite 5.0.8
✅ Tailwind CSS 3.3.6
✅ React Router DOM 6.20.0
✅ Recharts 2.10.3
✅ Framer Motion 10.16.16
✅ Axios 1.6.2

## Browser Compatibility

Tested on:
- Chrome 120+
- Firefox 120+
- Edge 120+
- Safari 17+

## Still Having Issues?

1. Check browser console (F12 → Console tab)
2. Check terminal for error messages
3. Verify backend is running: `http://localhost:8000`
4. Try incognito/private mode
5. Check network tab for failed requests

## Performance Tips

- Use production build for better performance: `npm run build`
- Enable React DevTools for debugging
- Monitor network requests in DevTools
