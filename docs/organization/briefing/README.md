# Sable Harbor Organization Briefing — v1.0

**Canonical date:** August 31, 2026  
**Format:** Executive briefing deck with one rendered image per slide  
**Brand source:** `assets/brand/logos/` — official geometric Sable Harbor logo system

This package uses the production Sable Harbor master mark and the production marks for Foundry Field, Willow, Atlas Meridian, Pale Sun, Project Cradle, American Resource Utility, Advisory, Red Wash Mine, and the Blood, Sweat & Tears Railway. No substitute clip art or generated lighthouse/compass imagery is used.

## Files

- [PowerPoint briefing deck](SABLE_HARBOR_Organization_Briefing_v1.0.pptx)
- [PDF briefing deck](SABLE_HARBOR_Organization_Briefing_v1.0.pdf)

## Individual briefing images

1. [Sable Harbor enterprise organization](images/01_sable_harbor_enterprise_organization.png)
2. [Foundry / Foundry Field](images/02_foundry_foundry_field_organization.png)
3. [Project Willow](images/03_project_willow_organization.png)
4. [Atlas Meridian](images/04_atlas_meridian_organization.png)
5. [Pale Sun / Red Wash](images/05_pale_sun_red_wash_organization.png)
6. [Project Cradle](images/06_project_cradle_organization.png)
7. [American Resource Utility / BS&T](images/07_american_resource_utility_bst_organization.png)
8. [Advisory](images/08_advisory_organization.png)

## Enterprise-chart fields

Every business-line card on the enterprise slide states:

- business-line name;
- headquarters or best-supported operating center;
- brief business description;
- current person in charge;
- current status.

Where headquarters, leadership, or organizational structure remains unresolved in canon, the slide states **OPEN** rather than inventing a permanent answer.

## Regeneration

```bash
npm install --no-save pptxgenjs@4.0.0
node tools/organization/build_org_briefing.js
```

The source builder reads official SVG marks directly from `assets/brand/logos/`.
