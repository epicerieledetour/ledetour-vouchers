- AC in a table [userid, flag], flag being an enum
- Just use history table, no vouchers.state
- Remove vouchers.label column
- Actually support expiration_date
- Adding new vouchers to system should add an history.state=0 entry
- Add user groups (easier to emit invoices to a group of multiple users)
- Name all date columns date_utc
- Voucher ID should be [#]-[random_hash]

* TODO
** Single CSV to initialize a campaign
** Simpler UI with /api/scan and /api/undo ?
** Single CLI

