# ETHstaker.tax

### Deployment

Before starting up all services, the necessary database structure needs to be created:

`make migrate`

Simply run `docker-compose up`. All necessary services will be started, which are:

- caddy - reverse proxy - exposed on ports 443, 80
- frontend - Vue3
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
once daily - every 24 hours.
On-demand balance retrieval from the beacon node would be time-consuming,
and for a year's worth of data would take quite a long time.
