# website

Michael Knapman's Website

This is my professional portfolio attached to my real name, where I publish
interesting code, cool lists, literary ideas.

I want to host the website source code on GitHub so that my content is git
tracked so you can see my projects change over time.

Every git push automatically updates https://michael.nekoweb.org/ thanks
to https://github.com/indiefellas/deploy2nekoweb
Files not able to be pushed by deploy2nekoweb such as the custom cursor
and linter are placed into the "hardcoded" folder.
Files containing unorganized conent not yet on the website is in the "content" folder.

## Build step

Run this before git add/commit/push to inject the fixed left-hand sidebar into every
page in `public/`:

    python3 build_site.py

The sidebar is a hierarchical sitemap of the site, generated from the folder
structure: a page named `<section>.html` acts as the landing page for the
sibling folder `<section>/`, so pages inside `engineering/` appear as
children of `engineering.html`. `index.html` is listed first as "Home".
Links are injected relative to each page's own folder.

Special folders:
- `media/`  - assets only (images, music). Never scanned, no sidebar, not listed.
- `unlisted/` - secret pages. They get the sidebar but are never listed in it;
  reach them by typing the URL or exploring the site.

The build is idempotent: re-running it replaces old injected sidebars
instead of duplicating them, so run it after every edit.

Mobile: the sidebar is responsive — on phones (max-width 600px) it turns
into a full-width top bar so the content uses the whole viewport instead
of a side column.

## Test step

Test the website in VScode terminal by running:
    python3 -m http.server 8000 --directory public

## Push step

Simply git push, and the deploy.yml mirrors the code onto the website!


## TODO

Make a topbar and bottom bar for code reuse and navigation.
Add copyright and software license directly on bottom of website.
Add a sitemap page.
Manually write HTML for all my content. Consider one time use with a static site generator. Possible inspiration: https://www.contentstack.com/blog/all-about-headless/what-is-a-static-website-learn-why-its-perfect-for-speed-and-security and https://www.contentful.com/blog/what-is-a-static-website/
Add buttons to link to github and linkedin.
Add a guestbook.
Join https://1mb.club/ webring

IDEAS:
Toothbrush recommendation page, referencing https://www.animated-teeth.com/electric_toothbrushes/oral-b-best-electric-toothbrushes.htm
Wifi referencing https://www.wiisfi.com/
USB speeds and power delivery and how im sad USB 3.2 Gen 2x2 is a failed standard that didn't catch on, so that USB 3.2 Gen 2x1 is the fastest common non-tunnelling USB speed at 10Gbps, making the Infineon FX20 useless.
List of my most favourite most-robust ETFs such as IAUM or ZGLD.TO, explaining mechanisms referencing: https://rpc.cfainstitute.org/research/foundation/2015/a-comprehensive-guide-to-exchange-traded-funds-etfs https://rpc.cfainstitute.org/research/foundation/2025/guide-to-etfs https://rpc.cfainstitute.org/research/foundation/2026/evaluating-etfs-module-2
Tax limitations of multi-cryptocurrency index funds like K1 tax forms.
Talk about PHY sizes on silicon, explaining why USB 2.0 is still so common, and why chips have so few PCIE lanes. Reference https://www.techpowerup.com/347141/intel-core-ultra-series-3-panther-lake-h-die-annotated
Tamagotchi tamatown shrine.


## Legal

Source code is licensed under the MIT License. Written content is licensed under CC BY-NC-SA 4.0.
Copyright © 2026 Michael Knapman. All Rights Reserved.
