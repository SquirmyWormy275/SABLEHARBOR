from pathlib import Path
import hashlib
import json
from PIL import Image

root = Path('docs/organization/briefing')
images = sorted((root / 'images').glob('*.png'))
if len(images) != 8:
    raise SystemExit(f'Expected 8 slide images, found {len(images)}')
for image in images:
    with Image.open(image) as im:
        width, height = im.size
        ratio = width / height
        if width < 1500 or height < 800 or abs(ratio - (16 / 9)) > 0.02:
            raise SystemExit(f'Unexpected slide image geometry for {image}: {im.size}')
        print(f'{image}: {width}x{height}')

readme = '''# Sable Harbor Organization Briefing — v1.0

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
'''
(root / 'README.md').write_text(readme, encoding='utf-8')

files = [
    root / 'README.md',
    root / 'SABLE_HARBOR_Organization_Briefing_v1.0.pptx',
    root / 'SABLE_HARBOR_Organization_Briefing_v1.0.pdf',
    *images,
    Path('tools/organization/build_org_briefing.js'),
]
records = []
for file in files:
    records.append({
        'path': file.as_posix(),
        'bytes': file.stat().st_size,
        'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
    })
manifest = {
    'package': 'Sable Harbor Organization Briefing',
    'version': '1.0.0',
    'canonicalDate': '2026-08-31',
    'officialLogoDirectory': 'assets/brand/logos',
    'slideCount': 8,
    'oneImagePerSlide': True,
    'files': records,
}
(root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print('Validated 8 rendered slides and wrote briefing manifest.')
