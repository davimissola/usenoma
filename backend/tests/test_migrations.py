from pathlib import Path

from alembic import command
from alembic.config import Config


def test_models_match_the_applied_migrations():
	config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
	command.check(config)
