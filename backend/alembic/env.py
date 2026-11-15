from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# ---------- 加载项目配置和模型 ----------
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.models.user import User  # noqa: F401,E402
from app.models.deck import Deck  # noqa: F401,E402
from app.models.card import Card  # noqa: F401,E402
from app.models.tag import Tag, card_tags  # noqa: F401,E402
from app.models.schedule import CardSchedule  # noqa: F401,E402
from app.models.review_log import ReviewLog  # noqa: F401,E402
from app.models.study import StudySession, LearningGoal  # noqa: F401,E402
from app.models.ai import SourceDocument, AiTask, AiGeneration  # noqa: F401,E402
from app.models.practice import ExamRecord, InterviewSession  # noqa: F401,E402
from app.models.card_link import CardLink  # noqa: F401,E402
from app.models.feynman import FeynmanSession, FeynmanExplanation  # noqa: F401,E402

config = context.config

# 覆盖 sqlalchemy.url
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
