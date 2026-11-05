# GoSWAPPS Studios

The official static website for GoSWAPPS Studios, an independent app studio based in Sweden.

## Local development

No installation, build step, environment variables, or runtime dependencies are required. From the existing checkout:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Open the local server in your browser. Edit `index.html`, `privacy.html`, `404.html`, `styles.css`, and the local files in `assets/` directly. Use the existing checkout; a separate Git worktree is unnecessary.

## Validation

Run the dependency-free repository checks:

```sh
python3 -m unittest discover -s tests -v
```

These eight tests cover page structure, local links and fragments, metadata, the sitemap, product statuses, image dimensions, and the absence of scripts, forms, embedded third-party resources, and tracking features. They do not replace browser testing.

For browser and HTML checks, install test-only tools **outside** this checkout (Node.js is needed only for these tests):

```sh
npm install --prefix /tmp/goswapps-web-validation --cache /tmp/goswapps-npm-cache --no-package-lock --no-save playwright@1.62.1 axe-core@4.11.1 html-validate@11.18.0
npx --prefix /tmp/goswapps-web-validation playwright install chromium
NODE_PATH=/tmp/goswapps-web-validation/node_modules node tests/browser.cjs
/tmp/goswapps-web-validation/node_modules/.bin/html-validate index.html privacy.html 404.html
```

Start the Python server first. If Chromium is already installed, skip the browser download and set `CHROMIUM_PATH` when running the browser checks:

```sh
NODE_PATH=/tmp/goswapps-web-validation/node_modules CHROMIUM_PATH=/usr/bin/chromium node tests/browser.cjs
```

The browser test defaults to `http://127.0.0.1:8000/`; `SITE_URL` can override this for local testing. It checks all three pages at 320, 375, 390, 768, 1024, and 1440 pixels, keyboard navigation, 200% text size, reduced motion, print styles, JavaScript-disabled navigation, network requests, browser storage, and WCAG 2.2 AA rules with axe-core. Automated checks do not establish full accessibility conformance. Screenshots are saved outside the checkout, to `/tmp/goswapps-web-validation/screenshots/`.

`assets/social-card.svg` and `assets/favicon.svg` are the editable sources for the committed PNG exports. The social card is 1200 × 630; the PNG favicon is 32 × 32; the touch icon is 180 × 180. Re-export these if their SVG sources change.

## Content and privacy

- MindReset: iOS calm and focus app; App Store review pending.
- ActionBridge: iOS tool for turning shared screenshots and notes into Calendar events and Reminders; in development.
- Hush: overnight snoring recording app; in development. No platform is asserted.
- The geometric app artwork is illustrative; it does not depict app screens or assert additional features.
- No download links, release dates, testimonials, or usage metrics are presented.
- No JavaScript, cookies, analytics, forms, external fonts, API calls, or third-party assets are used by the website. Contact and support use email links. The privacy page links to GitHub's privacy statement; this is a normal link, not an embedded resource.
- `privacy.html` describes this website only; it is not an app privacy policy. The privacy notice distinguishes hosting-provider request processing from site tracking.

## Hosting and publication

The repository root is directly compatible with GitHub Pages: `.nojekyll` opts out of Jekyll processing, and `404.html` provides the error page. The main and privacy pages use relative asset paths. The 404 page uses root-relative paths so that assets and navigation work at nested missing URLs on the intended domain. For a project-subdirectory deployment without a custom domain, adjust the 404 page's paths before publishing.

`sitemap.xml`, canonical URLs, and social metadata target the intended domain, `https://goswapps.com/`. `robots.txt` permits indexing after publication; it does not publish or register the site.

**Publication requires Peter's approval.** This change does not enable GitHub Pages, configure a custom domain, modify DNS, or publish the site. No deployment workflow or `CNAME` file is included. After publication is separately approved and the domain is configured, verify HTTPS, both sitemap URLs, the custom 404 page, social-card delivery, and email links on the actual host. Python's local file server does not automatically serve the custom 404 for missing URLs; the local browser checks visit `404.html` directly. Email delivery and mailbox configuration are outside this repository.
