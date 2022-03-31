# ETH2.tax

### Deployment

Before starting up all services, the necessary database structure needs to be created:

`make migrate`

Simply run `docker-compose up`. All necessary services will be started, which are:

- caddy - reverse proxy - exposed on ports 443, 80
- frontend - FastAPI
- API - FastAPI
- a Lighthouse beacon node
- balance indexer
- DB - PostgreSQL
- DB management - adminer - exposed on port 8080
- cache - Redis
- monitoring stack
  - Prometheus, Grafana, node_exporter, pg_exporter - Grafana exposed on port 3000

### Monitoring & debugging

There are some predefined dashboard available in Grafana. Those can be accessed
at [localhost:3000](http://localhost:3000) .

### Development

#### Dependency changes

Dependencies are managed by `pip-tools` . When you want to add/remove
a dependency, add it to [requirements.in](requirements.in) and then
run `make compile-dependencies`.
For upgrading/downgrading dependencies, run `make upgrade-dependencies`
to upgrade all package versions or `make upgrade-dependencies PACKAGE_NAME=pytest`
to upgrade one of them.

#### DB structure

If changes need to be made to the database, edit
[src/db/tables.py](src/db/tables.py) as needed.
Afterwards, run

`make migration-generate MIGRATION_NAME="my migration description"`

Alembic will automatically generate the necessary migration scripts under
[alembic/versions](alembic/versions). Go over them to make sure they were
correctly generated. Then migrate the database to the updated version using
`make migrate`.



### Space requirements

For each validator, its balance is stored in the database
approximately every 30 minutes (for every major timezone as defined by pytz).
On-demand balance retrieval from the beacon node would be time-consuming,
and for a year's worth of data would take quite a long time.

This takes up quite a lot of space. At the time of writing (March 31st 2022),
it takes up 204 GB, so about 13 GB / month. The more validators there are,
the quicker the growth.

These are some ideas I've had on reducing the database size:

- only store the balances for one timezone, e.g. UTC
- make the rewards calculation an async operation - e.g. the user requests the data,
  and can find them an hour later on the website based on the previous request
  - this way a small amount of data could be stored for a limited time period (1 day or week)
