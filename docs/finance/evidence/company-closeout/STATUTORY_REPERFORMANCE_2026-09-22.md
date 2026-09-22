# Statutory financial reperformance receipt

**Prepared:** September 22, 2026 UTC  
**Reviewed source:** `de542b83cbcb96d447b5b608faf88fea95a75bc3`  
**Scope:** Clean company-closeout acceptance candidate; this receipt does not itself establish repository acceptance or an external filing.

## Results

- All 124,344 journal legs form 54,019 balanced entity/scenario entries.
- The separate posting replay matched 8,605 statutory legs, including exact entity, period, source and account. Its role is implementation verification.
- The independent workpaper accounting check passed 90 taxpayer-year reconciliations, separately comparing current expense, gross deferred balances, prepayments, payable balances and source cash.
- The penalty source-to-journal check matched 501 legs and confirmed zero new cash or reposted tax principal.
- Five bounded iterations converged. Final changes in cash plans, settled-state deductions and business-interest deductions were all zero.
- Parent federal deductions equal all modeled paid state income taxes, including the separate West Virginia component. A federal loss carryforward does not eliminate the 20% taxable-income floor where the 80% limitation applies.

## Selected base-case results

Amounts are USD. Income-tax expense below means current provision, not deferred expense or sales tax. Future years remain conditional scenarios.

| Year | SHI current income tax | SHIH | PS, including RWH | ARU | BST | Total modeled income-tax cash paid |
|---|---:|---:|---:|---:|---:|---:|
| 2026 | 800.0000 | 800.0000 | 800.0000 | 0 | 0 | 945,886.0000 |
| 2027 | 800.0000 | 800.0000 | 800.0000 | 149,100.3371 | 11,795.1195 | 14,196.0000 |
| 2028 | 800.0000 | 800.0000 | 800.0000 | 172,970.9867 | 19,073.2659 | 21,472.0000 |
| 2029 | 835.6504 | 800.0000 | 800.0000 | 187,957.3931 | 24,363.8715 | 26,799.6504 |
| 2030 | 144,677.1562 | 800.0000 | 4,595.8990 | 203,086.3811 | 29,849.6595 | 179,921.1562 |
| 2031 | 76,136.2847 | 800.0000 | 25,114.7939 | 793,233.6009 | 35,692.0275 | 830,349.2847 |

The 2026 cash includes preserved ARU estimates of $813,743 and mine estimates of $131,343; overpayments remain assets and are not refunds. Current provision and cash therefore differ legitimately. Taxpayer/jurisdiction credits do not cross-offset.

At August 31, RWH's ROT payable is $1,944,457.78: $646,624.38 opening accrual plus $1,297,833.40 current activity. Separate penalties of $154,529.42 and interest of $50,815.81 total $205,345.23. The September 14 penalty/interest workpaper totals $211,406.82. No settlement is inferred.

The original ARU book goodwill remains $14,762,500; original tax goodwill remains separately identified as $13,000,000, with the existing $900,000 facilitative-cost tax-basis successor disclosed separately. Core goodwill removal remains exactly $30,000,000, with no cash or automatic tax deduction.

## Funding and adverse results

Base 2027 member cash is $17,627,792 across seven source events: $12,000,000 Core and $5,627,792 industrial. This is the after-tax successor result; the separate historical seven-source $13,325,751.3907 bridge remains a predecessor comparison.

Base member cash falls to zero in 2031, but that does not establish sovereignty. The report still shows $18,103,093.6059 booked tax cash requirements and negative $10,816,021.4621 internally available cash before growth. Base 2027 and 2028 booked requirements exceed consolidated cash by $11,755,370.5277 and $14,400,997.3403. Entity cash restrictions and other needs remain separate; aggregate cash is not permission to transfer it.

Historical round receipts remain $183,000,000. The separately authored completion of the existing $44,312,500 industrial contribution model produces total historical paid-in capital of $227,312,500 without another 2026 posting or new interests.

## Reviewed artifact hashes

Paths are under `enterprise/generated/company-closeout-v1/` at the reviewed source revision.

| Artifact | SHA-256 |
|---|---|
| `enterprise/enterprise_journal.csv` | `58bd00b5cd22fb7016545a228f0bc02f99ffa743e192144409354992417c05ce` |
| `statutory_current.json` | `af06a2947cd42832e255400edb72e359c8e46eee769da09bf6b928387be61cd8` |
| `statutory_deferred.csv` | `248b1abe08f1c4cf407f99c58b3129f314bda96bd3295de342c568229bbba5c8` |
| `statutory_payment_allocations.csv` | `68e3c2c8b34c383b67b598de56735a905e517fd48c1e5ff3c660681a8027f8ec` |

Reproduce through `python -m enterprise.closeout.build`, using the supported environment and clean checkout. The release's final accepted revision requires its own regeneration/identity receipt; this dated candidate evidence remains historical if later metadata or source changes alter hashes.
