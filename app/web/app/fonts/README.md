# Repository-local fonts

These files preserve the app's existing typography while removing the
production build's dependency on the live Google Fonts service. Next.js bundles
them through `next/font/local`; browsers do not contact Google Fonts.

The WOFF2 files are the byte-for-byte Latin assets emitted by the last successful
`next/font/google` production build on 2026-07-19. They were copied without
conversion or subsetting. The source request and upstream family records are:

- [Inter CSS2 request](https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap) and [Google Fonts metadata](https://github.com/google/fonts/tree/main/ofl/inter)
- [Spectral CSS2 request](https://fonts.googleapis.com/css2?family=Spectral:wght@400;500;600;700&display=swap) and [Google Fonts metadata](https://github.com/google/fonts/tree/main/ofl/spectral)
- [IBM Plex Mono CSS2 request](https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap) and [Google Fonts metadata](https://github.com/google/fonts/tree/main/ofl/ibmplexmono)

All three families are distributed under the SIL Open Font License 1.1. Their
family-specific copyright notices and license texts live beside the assets as
`OFL.txt`.

| File | Weight | SHA-256 |
| --- | --- | --- |
| `inter/inter-latin-variable.woff2` | 400–700 | `c940764593d0fe5d596be327ca7558855e018039fb78509aa21921fd3644c3e4` |
| `spectral/spectral-latin-400.woff2` | 400 | `bcb83e9c56d40c5111a2bdbc3d8bdabf66bd31337e968f1c223b61879b8d3cad` |
| `spectral/spectral-latin-500.woff2` | 500 | `79ce505722da87b9a2fa21a16cd0d7f426f1624fd16413e11be377bc9e922a3b` |
| `spectral/spectral-latin-600.woff2` | 600 | `1fb6ca29fc243e8bfdfce12d8d6806f322bcc62d38036986812be28fb1f41f0a` |
| `spectral/spectral-latin-700.woff2` | 700 | `1125ec621f11c8669efc3a86cc05d9e9e221853d2b1c9658d9e30de9d3b90bba` |
| `ibm-plex-mono/ibm-plex-mono-latin-400.woff2` | 400 | `c36f509c0a8f9f85f29cb44bc8701d8a9e0b14c499e77a884f789ead7093a7ac` |
| `ibm-plex-mono/ibm-plex-mono-latin-500.woff2` | 500 | `a76f53ca6612e7b3828eec2311098675b7f9849ae4169a8bcef6302aec02a6c0` |

Do not regenerate or replace an asset without updating its hash and retaining
the corresponding license. The app intentionally uses upright Latin faces only;
unsupported glyphs fall through to the declared system fallback stack.
