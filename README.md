# Sentinel-2 NDVI Explorer — Render deployment

## Included
- `app.py` — Flask app
- `templates/index.html` — form and result page
- `requirements.txt` — Python dependencies
- `Procfile` — Gunicorn start command

## Deploy on Render
1. Extract this ZIP.
2. Upload these files to a new GitHub repository (keep `templates/index.html` inside the `templates` folder).
3. In Render, choose **New + → Web Service** and connect the repository.
4. Use these settings:
   - Runtime: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
5. Deploy and check the Render-provided `onrender.com` URL first.
6. Once it works, add a custom subdomain such as `ndvi.tamilspacetech.com` in Render and create the DNS record Render tells you to add at your DNS provider.

## Notes
- This app accesses public Sentinel-2 assets online; first requests may take time.
- The app currently searches up to 10 items and uses the first result, as written in the supplied `app.py`.
- Test the default location and year in the deployed app before adding a custom domain.
