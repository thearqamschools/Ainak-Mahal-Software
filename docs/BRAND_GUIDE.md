# Ainak Mahal visual system

Original eyeglasses artwork created for this repository. No stock graphics, external logos or web fonts are included. The transparent mark works at 24px and larger; the navy application tile includes 16–256px ICO frames. Keep clear space of at least one bridge width. Preserve proportions, use a single navy/white ink with the teal bridge, and do not add school branding.

The chosen softly rectangular frame is an optical-store identifier with a compact silhouette. Rounded and angular alternatives are documented in `assets/brand/concepts.svg`; the rounded rectangle balances familiarity with small-size legibility. SVG is authoritative scalable artwork; PNG/ICO exports are committed so the installed app needs no imaging dependency. `python tools/generate_brand.py` regenerates exports with development-only Pillow. PNG lockup typography uses the installed Segoe/DejaVu font; SVG uses the viewer's Segoe/sans-serif fallback.

| Token | Colour | Use |
| --- | --- | --- |
| Navy | `#142D4E` | Navigation, brand, headings |
| Royal blue | `#2563EB` | Primary actions and focus |
| Teal | `#0D9488` | Bridge and contextual success accents |
| Canvas | `#F8FAFC` | Workspace |
| White | `#FFFFFF` | Forms, cards, tables |
| Main text | `#0F172A` | Labels and values |
| Muted | `#52647A` | Secondary text on light surfaces |
| Line | `#E2E8F0` | Input borders and separators |
| Error | `#B42318` | Inline error copy |

Segoe UI on Windows; supported DejaVu Sans/Helvetica fallback for Linux development. Body 10pt; secondary 9pt; screen titles 26pt; values 25pt. Use 8/12/16/24px rhythm. White-on-blue primary actions, high-contrast focus and selected-row treatment, explicit labels and scrollbar access. Never encode an essential status by colour alone.

Motion is limited to native hover, focus and press feedback. Account retry delay is a visible disabled state and rate-limiting feedback, not decorative motion. There are no fades, animated page transitions or chart motion; POS responds immediately and works offline.

Light artwork uses navy/teal on a light surface. `ainak-mark-dark.svg/png` and `ainak-lockup-dark.svg` use white/mint transparent artwork for navy surfaces; `ainak-lockup-dark.png` includes the navy background. Do not place white dark-surface artwork on white paper; printed documents use the navy light-surface mark.
