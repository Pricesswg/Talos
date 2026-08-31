# Brand assets

| File | Size | Format |
|---|---|---|
| `icon.png` | 256x256 | PNG RGBA, transparent background |
| `logo.png` | 512x288 | PNG RGB, opaque background |

HACS accepts brand assets from inside the repository, so the `brands` check
passes without waiting on a PR to `home-assistant/brands`.

## If these ever go to the default store

`home-assistant/brands` wants them under `custom_integrations/talos/` and
enforces a **maximum height of 256** for the logo. The current one is 288 and
will need resizing or cropping at that point. For in repo HACS use it is fine
as it stands.

`scripts/make_brand.py` (standard library only) generated the original
placeholders and is kept for reference.
