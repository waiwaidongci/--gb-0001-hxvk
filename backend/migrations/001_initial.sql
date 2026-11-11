-- Initial schema is created from SQLAlchemy metadata during bootstrap.
-- Database constraints intentionally enforce user email, dataset name, experiment name,
-- and (dataset_id, subject) uniqueness. In production use reviewed Alembic migrations.
CREATE INDEX IF NOT EXISTS observations_dataset_idx ON observations (dataset_id);
CREATE INDEX IF NOT EXISTS analysis_runs_experiment_idx ON analysis_runs (experiment_id);
