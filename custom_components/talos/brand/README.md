# Brand assets

`icon.png` (256x256) e `logo.png` (512x256) sono **segnaposto** generati da
`scripts/make_brand.py`. HACS li accetta da dentro il repository, quindi
sbloccano il check `brands` senza aspettare una PR a `home-assistant/brands`.

Per sostituirli basta sovrascrivere i due file mantenendo nomi, percorsi e
dimensioni: nessun altro file fa riferimento a loro. Entrambi PNG a 8 bit con
canale alpha.

Quando l'integrazione verra' proposta allo store predefinito di HACS serviranno
anche nel repository `home-assistant/brands`, sotto `custom_integrations/talos/`,
con le stesse specifiche.
