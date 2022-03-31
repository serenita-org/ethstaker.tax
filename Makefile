compile-dependencies:
	docker-compose run --rm --name "compile-dependencies" -v "$(PWD)":/app -w /app api bash -c "pip install pip-tools && pip-compile --generate-hashes"

upgrade-dependencies:
	docker-compose run --rm --name "upgrade-dependencies" -v "$(PWD)":/app -w /app api bash -c "pip install pip-tools && pip-compile --generate-hashes --upgrade $(PACKAGE_NAME)"

migrate:
	docker-compose run --rm --name "db_migrate" -v "$(PWD)":/app api bash -c 'while !</dev/tcp/db/5432; do sleep 1; done; alembic upgrade head'

migration-generate:
	docker-compose run  --rm --name "db_migration-generate" -v "$(PWD)":/app api bash -c 'while !</dev/tcp/db/5432; do sleep 1; done; alembic revision --autogenerate -m "$(MIGRATION_NAME)"'

test:
	docker-compose -f docker-compose.test.yml --env-file .env.test run --rm test_runner pytest
