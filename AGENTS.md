# xtra.agency.ua

## Cursor Cloud specific instructions

This repository is a **fully static single-page marketing website** (plain HTML5, CSS3, vanilla JS) for the Ukrainian web agency "Xtra Agency". There is **no build system, package manager, backend, database, or automated test/lint tooling**.

- **Files:** `index.html` (the whole page), `css/style.css`, `js/main.js`, and static images under `assets/`.
- **No dependencies to install.** There is no `package.json`, lockfile, `requirements.txt`, or `Makefile`. The update/setup step is effectively a no-op.
- **Run in dev mode:** serve the repo root with any static server, e.g. `python3 -m http.server 8080` from `/workspace`, then open `http://localhost:8080/`. Opening `index.html` directly in a browser also works.
- **Tailwind + Google Fonts load from CDNs** (`cdn.tailwindcss.com`, Google Fonts). Without internet access the page still works via `css/style.css` but loses Tailwind utility styling and the Manrope font.
- **Forms are client-only stubs:** the consultation modal (`#consultForm`) and site configurator (`#siteConfigurator`) in `js/main.js` call `preventDefault()` and show a JS `alert()`; nothing is sent to a server.
- **No lint, no tests, no build.** Verification is manual: serve the site and confirm interactivity (menu, FAQ accordion, reviews slider, consultation modal + success alert).
- **Deployment:** `.github/workflows/deploy-pages.yml` publishes the repo root to GitHub Pages on push to `main`; there is no compile step.
