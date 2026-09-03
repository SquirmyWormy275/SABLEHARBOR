# SABLE HARBOR — PUBLIC REPOSITORY AND WIKI POLICY

**Version:** 0.1.0  
**Date:** August 31, 2026  
**Status:** LOCKED repository-governance decision

## 1. Public visibility is intentional

The Sable Harbor repository is intentionally public. Public visibility supports a browsable institutional archive, transparent project history, and a public GitHub wiki.

This decision supersedes the earlier statement in the preserved canonical architecture handover that described the repository as private. The handover remains unchanged as a historical source; this policy controls current repository visibility.

Public access is not an open-source license. Unless a specific file states otherwise, all rights are reserved and no permission is granted to copy, modify, distribute, sublicense, or commercialize the contents.

## 2. Canon remains in the repository

Versioned documents under `docs/canon/` are the controlling source of truth.

The wiki is secondary. Its purposes are to:

- provide readable institutional history;
- explain products, programs, people, facilities, and terminology;
- provide chronological and thematic navigation;
- link readers to controlling canon documents;
- distinguish LOCKED, PROVISIONAL, OPEN, and SUPERSEDED material.

A wiki page does not lock canon merely because its prose is polished. When a wiki page conflicts with a controlling canon document, the canon document controls.

Material changes to history, identity, chronology, or decision state should be made through repository review first and reflected in the wiki afterward.

## 3. No Easter-egg index

Sable Harbor will not maintain a standalone Easter-egg index, decoder, checklist, or exhaustive explanation page.

Easter eggs may remain embedded in:

- names;
- project titles;
- equipment and model identifiers;
- locations;
- quotations;
- expense-report stories;
- internal terminology;
- and corporate archaeology.

The wiki may describe an artifact naturally when it belongs in the history. It should not decode the outside reference, identify the real-world inspiration, or gather Easter eggs into a discoverable master list.

## 4. Public-content boundary

The following must not be published in the public repository or wiki:

- hidden benchmark ground truth;
- evaluation oracles and answer keys;
- credentials, tokens, keys, or private endpoints;
- unreleased scenario solutions;
- private personal information about real people;
- proprietary NAILEX implementation details that are not deliberately released;
- customer-confidential or legally restricted material;
- security-sensitive operating details whose disclosure would create avoidable risk.

When Sable Harbor requires hidden truth or spoiler-sensitive benchmark material, that material must live in a separate controlled repository, private release package, or local generation environment. Public canon may describe the existence and boundaries of such material without revealing it.

The designated private evaluator control plane is `SABLEHARBOR-ALEXANDRIA-CONTROL`. Public files
may identify its existence and purpose and may carry non-revealing version/checksum references;
they must not reproduce its hidden physical or causal truth, actor knowledge state, seeded
exceptions, expected detections, scoring rubrics, leakage tests, or evaluator answers.

## 5. Wiki-page discipline

Substantive wiki pages should identify:

- the page's subject;
- the applicable canon state;
- the controlling repository source or sources;
- the last substantive review date;
- any unresolved or provisional details.

The wiki may use a more narrative style than the canon documents, but it must not silently collapse uncertainty, rewrite chronology, or convert authorial inspiration into in-world fact.

## 6. Initial wiki scope

The initial wiki may cover:

- Home and navigation;
- corporate history;
- Blackridge and the founding;
- the Original Eight and later people;
- Foundry and Foundry Field;
- The Crossing;
- Evalon, Emberline, and Willow;
- Atlas Meridian;
- Pale Sun and Red Wash;
- Project Cradle;
- American Resource Utility and BS&T;
- Advisory;
- locations and facilities;
- timeline;
- glossary;
- canon and continuity policy.

An Easter-egg index is expressly excluded.
