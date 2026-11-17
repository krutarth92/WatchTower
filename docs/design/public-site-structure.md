# WATCHTOWER public site structure

Status: owner-directed Task 34 amendment, 2026-10-23.

## Purpose

WATCHTOWER needs a coherent public information architecture around the working
search and actor research flows. The owner supplied two visual references: the
live CyberNetSec.io home page and a composite concept image covering the
possible WATCHTOWER modules. They are design references, not templates or
instructions to copy content, branding, metrics, maps or implementation.

The resulting site keeps WATCHTOWER's open editorial presentation, shared
design tokens and evidence-first semantics. It avoids a dashboard of repeated
boxes and avoids claims the current published-read API cannot support.

## Public navigation

| Module | Route | V1 purpose |
| --- | --- | --- |
| Home | `/` | Latest published intelligence, important actor entry points and the newest platform update. |
| Intelligence | `/advisories` | Published living advisories, current articles, historic revisions and ordered updates. |
| Actors | `/actors` | Published actor directory drawn from the current discovery contract. |
| Evolution | `/evolution` | Entry points into actor histories; complete event detail remains on the actor dossier timeline. |
| Research | `/search` | Deterministic search for actors, techniques, indicators, CVEs and related context. |
| Technical | `/technical` | Read-only guide to ATT&CK, Sigma and STIX capabilities and their current availability. |

`/updates` is a secondary destination reached from the platform-update rail and
footer. It is a release archive, rather than a seventh primary research module.

## Platform updates

The CyberNetSec.io reference uses a narrow, prominent announcement rail below
its primary introduction. WATCHTOWER adapts that pattern with less visual glow:

- the home page shows the newest product change with date, short title and one
  relevant internal link;
- `/updates` lists the same real releases in reverse chronological order;
- one typed content module is the single source for both views;
- entries describe shipped, reviewable behavior only and never claim a future
  item is available;
- the update rail is visually distinct from threat intelligence so users do
  not mistake product news for a security finding.

## V1 and later boundaries

- The actor dossier and evidence remain within the existing actor workspace.
  A standalone evidence/source profile waits for a public detail API.
- Evolution uses published event data already available per actor. It does not
  chart one cursor page as a complete history.
- Research stays deterministic search. `Ask WATCHTOWER` remains unavailable
  until RAG is configured and evaluated.
- Technical is informational in V1. Public STIX generation, raw-artifact
  controls and Sigma generation remain outside the unauthenticated browser
  boundary.
- The composite image's enterprise environment dashboard remains V2 work,
  alongside AWS deployment and operational proof.

## Presentation rules

- Primary pages use open editorial sections, whitespace and horizontal rules.
  Borders support dense records only where they clarify grouping.
- Navigation, release content, section labels and visual values each have one
  authoritative source.
- Color, typography, spacing, radius, shadow and motion values remain in the
  shared token file. Page components contain no color literals.
- The header must remain keyboard usable and fit at 320 CSS pixels without
  horizontal page overflow. Mobile navigation may wrap or scroll within its own
  labelled region.
- All records come from published public routes. Drafts, operator tokens and
  private backend configuration never enter browser state.

## Task 34 implementation slice

Task 34 delivers the shared navigation, home page, platform update rail and
archive, the six useful module destinations, and the complete published
advisory journey. Actor, evolution and technical landing pages compose existing
published data and clearly state current capability limits. Task 35 then adds
deterministic demo data and Docker integration; Task 36 validates the complete
responsive flow.
