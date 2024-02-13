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


* How can I handle different data types in an Entity-Attribute-Value design (e.g. single table with multiple columns or multiple tables per data type)?
** https://stackoverflow.com/questions/18105644/how-can-i-handle-different-data-types-in-an-entity-attribute-value-design-e-g


# ARCH QUESTIONS ?

- gens queries in SQL directly or go through an API ? First case, DB is the API, second case, we do data transformation in python not in SQL (which is made for)


- Why unittest vs pytest ? pytest is nicer but it's one less dependency
- Do not run new subprocesses to test cli, too slow

- Data driver from database, no business logic should be outside of the database. If and For
  and for data presentation only

- All IDS can be public ?
* We will be leaking internal IDs, but what matters is that
  * User Bearer
    * are never public
    * can be changed quickly
    * are shared privately
  * VoucherID
    * cannot be guessed easily