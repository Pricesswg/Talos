# Brand assets

| File | Dimensioni | Formato |
|---|---|---|
| `icon.png` | 256×256 | PNG RGBA, sfondo trasparente |
| `logo.png` | 512×288 | PNG RGB, sfondo opaco |

HACS accetta questi asset da dentro il repository, quindi il check `brands`
passa senza aspettare una PR a `home-assistant/brands`.

## Se un giorno vanno nello store predefinito

`home-assistant/brands` li vuole sotto `custom_integrations/talos/` e impone
un'**altezza massima di 256** per il logo: quello attuale è 288 e andrà
ridimensionato o ritagliato in quell'occasione. Per HACS in-repo va bene così.

Generatore dei segnaposto originali: `scripts/make_brand.py` (solo stdlib),
tenuto come riferimento e non più usato.
