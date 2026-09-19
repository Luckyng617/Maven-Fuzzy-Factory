# Deploy the Interactive Dashboard

The Streamlit app remains interactive after deployment. It loads a compact session-level data model, then recalculates KPIs and charts whenever users change the date, channel, or device filters.

## 1. Build the deployable data model

Run locally after loading the source CSVs:

```bash
python3 load_data.py
python3 build_dashboard_data.py
```

This creates `dashboard_data.db`. It contains one row per session with the session attributes, pageview count, order count, and revenue. The full `fuzzy_factory.db` and raw CSVs are not needed by the hosted dashboard.

The build script checks that the session grain is preserved and rejects a database larger than GitHub's 100 MB per-file limit.

## 2. Push the project to GitHub

Create a **public** repository on GitHub, then run:

```bash
git init
git add .gitignore dashboard.py dashboard_data.db build_dashboard_data.py load_data.py make_charts.py fuzzy_factory_analysis.sql requirements.txt README.md DEPLOY.md linkedin_post.md charts/
git commit -m "Add interactive Maven Fuzzy Factory dashboard"
git branch -M main
git remote add origin https://github.com/<your-username>/maven-fuzzy-factory-analytics.git
git push -u origin main
```

Do not upload the raw CSVs or `fuzzy_factory.db`. They are excluded by `.gitignore` and are only needed to reproduce the analysis locally.

## 3. Deploy on Streamlit Community Cloud

1. Go to **share.streamlit.io** and sign in with your GitHub account.
2. Select **Create app → New app**.
3. Choose the repository and branch `main`.
4. Set the main file to `dashboard.py`.
5. Click **Deploy**.

The resulting `https://<your-app>.streamlit.app` URL is the interactive dashboard link for LinkedIn. Users can change the filters and the charts update in the browser.

## 4. Update the app

Any `git push` to `main` automatically redeploys the app. If the source data changes, rerun `build_dashboard_data.py`, commit the new `dashboard_data.db`, and push it.
