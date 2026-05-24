# Public account H5 and ad monetization

This project is already closest to a WeChat public-account H5 page. Publish it as an HTTPS website, then add the URL to a public-account custom menu.

## Recommended path

1. Host this directory as a static HTTPS site.
2. Configure the public account JS security domain and business domain to match the site domain.
3. In the public-account custom menu, choose a web-page jump and paste the HTTPS URL.
4. Add the site in Google AdSense and request review after the page is published.
5. Keep Auto ads enabled in AdSense, or replace the empty slot content in `js/ads.js` with fixed ad-unit code later.

## Google AdSense

The page includes the AdSense account tag and Auto ads loader for:

```txt
ca-pub-5678257058574392
```

The root `ads.txt` file contains:

```txt
google.com, pub-5678257058574392, DIRECT, f08c47fec0942fa0
```

## Ad slots

The page now contains two non-invasive slots:

- `top-banner`
- `bottom-banner`

By default these fixed slots are hidden because the site uses AdSense Auto ads. If you create fixed display ad units in AdSense, update `js/ads.js`:

```js
slots: {
  "top-banner": {
    html: "<!-- paste ad network code here -->"
  },
  "bottom-banner": {
    html: "<!-- paste ad network code here -->"
  }
}
```

## Mini program notes

A mini program can use official ad components after the account meets platform requirements, but this emulator depends on browser APIs, ROM files, and page-level JavaScript. Porting it to a mini program would be a rewrite and may face content and copyright review risk if bundled ROMs are not licensed.

For this codebase, H5 in the public-account menu is the fastest and lowest-risk launch path.
