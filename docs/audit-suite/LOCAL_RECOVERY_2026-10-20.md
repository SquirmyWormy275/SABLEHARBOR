# Local CLEAN/MESSY recovery, 20 October 2026

The installed workstation workrooms were recovered after an interrupted service
shutdown. This is an operating receipt for that private installation, not a new
company-source edition or a portable workroom database.

On 9 October, the user service timed out during shutdown and killed the workspace
child. Its session had a `READY` receipt but no normal stop or wait receipt. A
later start correctly reported `RECONCILIATION_REQUIRED`. Inspection found four
stale CLEAN SQLite sidecars, one signed logout record beyond the last saved
configuration in each room, and six expired role credentials. The original
session and sidecar bytes were preserved. The histories were copied and checked
before repair; no missing normal-stop receipt was invented.

The local operator reconciled the signed logout records, renewed credentials
through signed Store transitions and retained each room's audit history. The
unchanged launcher then reached `READY`. CLEAN remained at audit revision 6011
and MESSY at revision 6856. Both browser roots served HTTP 200. All six roles
authenticated; only operators could open the instructor Key. Auditors listed
their scoped company systems and downloaded previously collected originals
whose bytes matched the retained hashes. A normal stop produced stop and wait
receipts, and an explicit restart preserved both revisions and state hashes.

The dated private repair folder contains the full backup, exact manifests,
session receipts and credential transition evidence. It stays outside Git with
the credentials, instructor material and live workroom databases. The Seagate
recovery volume was unavailable, so the new backup was not independently copied
off the workstation. The renewed credentials have a seven-day lifetime starting
20 October; operators must check their expiry and renew them through a signed,
verified transition before later use.

If the launcher again reports `RECONCILIATION_REQUIRED`, preserve its state and
inspect session and process receipts before changing any pointer or database.
Do not reset a room, fabricate a normal stop, or substitute the public company
files for its retained audit history. The public [CLEAN/MESSY intake guide](CLEAN_MESSY_INTAKE.md)
remains usable independently of this local service.

The [23 October operational successor](LOCAL_RECOVERY_2026-10-23.md) records later
recovery, collection revisions and private GitHub preservation. It extends this
dated receipt; it does not replace the interrupted-shutdown history above.
