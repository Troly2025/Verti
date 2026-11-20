# VERTI — bilingual website and news archive

**Repository:** https://github.com/Troly2025/Verti  
**Production domain:** https://verti.ch  
**Existing Cloudflare Worker:** `steep-meadow-46e1`

This is an independent Vietnamese/English news publication about science, intellectual property and world trade. The website is a static build with zero database and **no paid CMS**. It preserves the existing VERTI navy/gold visual identity.

## Status

- Site source and site generator: in this GitHub repository.
- GitHub → Cloudflare automatic deploy: **not connected or verified yet**. Nothing in this commit changes the live site automatically.
- Archive: **4 historical Facebook posts** were recovered from the user's archived WIPO Work records, independently source-checked against original WTO/WIPO news pages, and saved as bilingual article data in `content/articles.json`. No fictitious articles were created. They are **not yet confirmed live on verti.ch**.
- Once linked to the **existing** Worker, changes merged to `main` can trigger Cloudflare deployment.

## One-time Cloudflare setup (keeps verti.ch)

1. Open https://dash.cloudflare.com/ → **Workers & Pages** → select **steep-meadow-46e1** (do **not** create a new Worker).
2. Open **Settings → Builds → Connect**.
3. Authorize/install Cloudflare's GitHub integration if prompted; select **Troly2025 / Verti**, production branch **main**.
4. Root directory: repository root (`/`). Build command: `npm run build`. Deploy command: `npx wrangler deploy`.
5. Check Worker name is `steep-meadow-46e1`, matching `wrangler.jsonc`. Review before promoting first build. The existing Worker must remain attached to the existing Custom Domain `verti.ch`. Do not edit nameservers, MX records or billing.
6. Confirm that both https://verti.ch and the English version https://verti.ch/en/ work after the first deployment.

Official reference: https://developers.cloudflare.com/workers/ci-cd/builds/ 

**Important:** Connecting an existing Worker does not automatically copy its currently deployed source into GitHub. This repository contains a newly authored compatible VERTI site. Preview before activating.

## Historical articles already prepared

- Panama's ITA II request (WTO; 19 November 2026)
- WTO 101 student event (WTO; 19 November 2026)
- WIPO–WTO senior-officials programme (WTO; 19 November 2026)
- Accessible textbooks in Kazakhstan (WIPO; 3 November 2026 source; Facebook 20 November 2026)

Each archived item carries its original source URL and Facebook permalink. Current archive graphics are editorial placeholders, not copied from third-party sources; original images and videos need separate rights and asset verification before reuse. Cloudflare publication is **pending the one-time Git integration**.

## Publishing verified articles

Edit `content/articles.json` in GitHub. Add **one article object** according to the fields below. Keep `status: "draft"` until all information is checked and the source/rights are verified. Then change status to `published` and commit. On connected Cloudflare Builds, this automatically creates two permanent article pages and updates homepage, archive, RSS and sitemap:

- Vietnamese: `https://verti.ch/articles/<slug>/`
- English: `https://verti.ch/en/articles/<slug>/`

Every article must have title, summary and body in both languages, a genuine original source URL, original publication date and an appropriate category. Images must be licensed/approved, with bilingual alt text and credits.

### Article object example — DRAFT ONLY

```json
{
  "slug": "sample-story-not-for-publication",
  "status": "draft",
  "category": "wipo-news",
  "date": "2026-11-20T12:00:00Z",
  "title": { "vi": "BẢN NHÁP – KHÔNG ĐĂNG", "en": "DRAFT – DO NOT PUBLISH" },
  "summary": { "vi": "Bản nháp minh họa cấu trúc.", "en": "Schema example only." },
  "body": {
    "vi": [{ "heading": "Bối cảnh", "paragraphs": ["Nội dung đã đối chiếu nguồn."] }],
    "en": [{ "heading": "Background", "paragraphs": ["Fact-checked copy."] }]
  },
  "source": { "name": "WIPO", "url": "https://www.wipo.int/" },
  "facebookPost": "",
  "facebookReel": "",
  "images": []
}
```

Do not copy this dummy object with `status: "published"`. It is only a schema example.

### Publishing checklist

1. Compare title, facts, dates, original source, images and image rights with the original material and the Facebook post.
2. Save the original Facebook permalink (for any old imported post), original date and linked Reel, if present. **Do not re-post the old Facebook article.**
3. Mark `published` only when both language versions are complete and verified. `scripts/build.js` excludes all drafts and rejects missing required fields.
4. Verify the site page URLs after Cloudflare has deployed. Never claim published from a GitHub commit alone.
5. Preserve stable slugs and review changes for duplicates. Do not add the same article twice.

## Run locally

Requires Node.js 18+.

```bash
npm run build
```

The build outputs static assets in `dist/`, including `/en/`, `/archive/`, article routes, `robots.txt`, `sitemap.xml` and `rss.xml`.

No backend, passwords or API tokens are kept in GitHub. Cloudflare deployment permissions are handled through its GitHub integration.

## Editorial boundaries

VERTI is independent, not an official WIPO, WTO, or government website. Source attribution and article verification are required. Importing old Facebook posts requires access to their actual full text and rights-cleared media, not headline inference.
