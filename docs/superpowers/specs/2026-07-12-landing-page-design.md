# Landing Page / Founder One-Pager — Design

## Purpose

A single public page that serves as both the "founder's one-pager" (linked
in direct outreach emails to AMR researchers) and the landing page for a
LinkedIn post promoting the project's current state. One artifact, two
audiences — no separate PDF to maintain in parallel.

## Audience & tone

Technical-credibility-first: lead with real results and honest methodology
(same voice the README already uses), written plainly enough that a
non-expert LinkedIn reader still follows it. Not two separate tracks —
good plain-English writing serves both audiences on one linear page.

## Call to action

Both the GitHub repo link and direct contact (email/LinkedIn) are present
with no forced hierarchy — this is a "here's what I'm building, here's the
evidence, talk to me or go look at the code" page, not a hard sales funnel.
Fits an early-stage, pre-funding, outreach-to-learn project.

## Content structure (single scrolling page)

1. **Hero** — "AcquireML", "GPS for your lab" tagline, one-line
   differentiation from predictive classifiers. Repo + contact links
   visible immediately.
2. **The problem** — antibiotic resistance urgency (Ciprofloxacin
   0% → 46% resistance since the 1980s), why lab experiments are the
   bottleneck.
3. **How it works** — the 6-step active learning loop (from README),
   as a clean numbered flow.
4. **Results** — the credibility section. Reuses existing
   `docs/*.png` charts (learning curves, holdout validation, feature
   importance) with the current numbers (post threshold-tuning fix:
   AZM 93.9% balanced accuracy / 89.9% recall, CIP 97.7%).
5. **Status** — honest "early-stage, actively building" framing with a
   short roadmap glance. Signals real in-progress work, not a polished
   sales pitch — matches the "reach out to learn, not pitch" outreach
   philosophy already in play.
6. **Contact / footer** — repo link, email/LinkedIn, license mention.

## Technical approach

Plain HTML + CSS + a small amount of vanilla JS. No framework, no build
step, no dependencies.

- **Why no framework:** it's one static page. A React/build pipeline would
  need a build step before GitHub Pages could serve it — pure overhead for
  content that changes rarely.
- **JS scope, explicitly bounded:** scroll-reveal animations (Intersection
  Observer — fade/slide sections into view as the user scrolls) and smooth
  scrolling for anchor links. Roughly 40 lines, inline or as one small
  `<script>` file, zero dependencies. This is progressive enhancement —
  the page is fully readable with JS disabled.
- **Images:** reuses existing chart PNGs already committed under `docs/`
  — no new chart generation needed.
- **Responsive/theme-aware:** relative units, mobile-first single column,
  images scale down, respects `prefers-color-scheme` for light/dark.

## Hosting

File lives at `docs/index.html` in the repo — GitHub Pages can serve
directly from the existing `docs/` folder (which already holds the chart
images the page reuses), avoiding any repo restructuring. Enabling Pages
itself (Settings → Pages → source: `main` branch, `/docs` folder) is a
manual GitHub UI toggle — out of scope for this implementation, flagged
as a follow-up step for Gabe once the page is committed.

## Process

Build the page, preview it live via the Artifact tool (a real browser
render, not a text description) for visual sign-off, iterate on feedback,
then commit the final version to `docs/index.html`.

## Out of scope

- No separate downloadable PDF — the hosted page URL is the shareable
  artifact for both outreach emails and the LinkedIn post.
- No CMS, no analytics, no contact form (mailto/LinkedIn links only).
- No new chart generation — reuses what's already in `docs/`.
