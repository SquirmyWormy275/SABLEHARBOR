# Read Sable Harbor company data from the repository

The company records are included in this repository so a cloud consumer can read
them without access to the author's computer, an external drive, credentials or
a running Sable Harbor workspace.

| Collection | Records | Where to start |
|---|---:|---|
| Accepted company source library | 5,714 record versions across 922 source systems and both retained histories | [Company records](company-records/README.md) |
| November client submissions | 70 artifacts and three original manifests | [Initial, follow-up and correction submissions](demo-2026-11/client-records/README.md) |
| Existing finance evidence | Billing, close, treasury, tax, customer and supporting schedules | [Finance evidence](../finance/evidence/) |

The broad library and November submissions are separate source editions. Their
identities, dates and declared relationships control; a shared company name does
not make every record interchangeable. The November scope describes which records
belong to its three selected procedures. The broad library supplies the retained
company data for other work without requiring the company generators.

## Publication authority

On 18 October 2026, the repository owner explicitly required the actual company
data to be placed in the repository for use by a cloud consumer. Keeping it only
on a workstation or external drive did not meet that requirement. This instruction
authorizes the complete accepted company-source export and the three existing
November client submissions in Git. It supersedes their earlier local-only
distribution arrangement when this change is merged into the controlling branch.

The publication covers synthetic company records, their delivery manifests and
the tools needed to verify them. It does not publish credentials, private evaluator
answers, licensed third-party source documents or completed auditor workspaces.
The company export documents any removal of workstation routing metadata and
retains the original source hashes. It must account for every one of the 5,714
source versions; source redaction must not become unreported record omission.

This is a repository delivery decision. It does not add company events, change
fictional dates, turn generated representations into original vendor records,
or establish an audit result. The [November publication record](demo-2026-11/PUBLICATION_2026-10-18.md)
pins the exact unchanged client manifests. New complete ZIP distributions continue
to follow the [release policy](../governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md).

## What the external-drive backups contained

The retained October 4 recovery instructions describe 34 ordinary compressed
backup archives on the Seagate drive, including older large CLEAN and MESSY
database snapshots. The October 7 recovery inventory distinguishes those backups
from the company systems used for collection. The earlier cleanup preserved the
accepted company library and active workspaces while retiring obsolete preparation
copies and caches.

For this publication, the accepted 5,714-version library was found locally and
verified independently of the external drive: its database matched the retained
accepted digest, its SQLite integrity check passed, and every record content hash
matched. The three November submissions also passed their original verifier.
Those checks establish the availability of the published records. They do not
claim to reverify every older recovery archive while the drive is disconnected.

The raw historical recovery archives and live auditor databases are not this
public company-data interface. Reading the company records above does not require
restoring them or recreating the original workstation.
