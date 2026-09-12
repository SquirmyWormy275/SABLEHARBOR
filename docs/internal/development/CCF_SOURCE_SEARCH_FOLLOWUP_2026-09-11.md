# CCF publisher-source search follow-up

The deeper search obtained both AICPA source documents from publicly indexed URLs in the same Contentful space (`rb9cdnjh59cm`) used by the official AICPA website. Downloads required no credentials. PDF titles, editions, page counts and SHA-256 hashes were checked. Originals remain outside the public repository. This closes the missing-local-copy issue for the named SOC 2 criteria editions, not source-inventory or mapping review.

| Document | Finding |
|---|---|
| AICPA TSC, 2017 with revised points of focus 2022 | Downloaded, 75 PDF pages, 567,612 bytes. The official landing page lists 554.3 KB, consistent with the downloaded size. |
| AICPA description criteria, 2018 with revised guidance 2022 | Downloaded, 36 PDF pages, 335,512 bytes. The official current listing names the same edition but lists 330.9 KB; exact byte identity with that account-download variant is not confirmed. |
| ISO/IEC 27001:2022 | No verified free full edition found. Official publisher purchase route remains available. |
| ISO/IEC 42001:2023 | No verified free full edition found. The current ISO catalog lists edition 1 (2023) and no separate amendment. |
| ISO/IEC 27001:2022/Amd 1:2024 | Official ISO/IEC stores list the amendment at CHF 0. Singapore's appointed distributor advertises a free download, but retrieval failed here. OBP returned informative material only. UNI supplies a public bilingual summary of the actual climate additions; it is supporting material, not the exact ISO amendment artifact. |

## Downloaded AICPA originals

- [aicpa-tsc-2017-pof-2022](https://assets.ctfassets.net/rb9cdnjh59cm/5jT1narHNQNzt4JGlkd1gr/248661d08e42531329d147782a6f8854/Trust-services-criteria.pdf); SHA-256 `23a099dd1dc273b7a45fda2351f376344c33fcb2911d586036c0e0d631b8ad69`.
- [aicpa-dc-2018-guidance-2022](https://assets.ctfassets.net/rb9cdnjh59cm/1vCduR1U2OnhIvFFaDBjMv/836050054707e9afb65adeb30d2e95d8/92317096_dc_section_200_clean_version.pdf); SHA-256 `81286ab2afbf98ede900366bd36b461fd0ca554e18342c403fcea3a33d2a6d98`.

## Verified access routes and limitations

- [AICPA TSC landing page](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022) and [description criteria landing page](https://www.aicpa-cima.com/resources/download/get-description-criteria-for-your-organizations-soc-2-r-report) still show account access; the indexed CDN URLs above respond publicly.
- [ISO 27001 + ISO 42001 English PDF package](https://www.iso.org/publication/PUB200427.html): CHF 342 on the package page at retrieval. Individual official listings are CHF 155 and CHF 225. No purchase made; checkout taxes and organizational use terms are separate.
- [ISO 27001 amendment](https://www.iso.org/standard/88435.html) and [IEC listing](https://webstore.iec.ch/en/publication/92579): no-cost acquisition route.
- [Singapore free-amendment listing](https://www.singaporestandardseshop.sg/Product/SSPdtDetail/907ccf03-cea6-bb62-4850-3a10e57074be): link identified; local DNS timed out and browser download failed.
- [UNI explanation](https://www.uni.com/cambiamenti-climatici-e-norme-sui-sistemi-di-gestione/) and [public supporting text](https://www.uni.com/wp-content/uploads/Modulo_Amd_ISO.pdf).
- [ISO's former freely available standards directory](https://standards.iso.org/ittf/PubliclyAvailableStandards/) now redirects readers to the ISO/IEC webstores; it does not provide an alternative full-text archive.
- [EVS ISO 42001](https://www.evs.ee/en/iso-iec-42001-2023) provides a preview and paid access. Its single-user download requires FileOpen, which the page says is unsupported on Linux; this is not a suitable default for this workspace.

Atlas remains an editorial reference. Neither Atlas nor a preview replaces a full normative source. Availability of the AICPA PDFs does not create accepted mappings, assessment conclusions or permission to redistribute publisher text in a public catalog. Existing generated workbench packages are unchanged.
