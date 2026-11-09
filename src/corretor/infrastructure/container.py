from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import corretor.plugins
from corretor.application.dto import CollectionOutcome
from corretor.application.services import CollectionService, PendencyService
from corretor.domain.entities import PluginContext
from corretor.domain.enums import RunStatus

from .clock import SystemClock
from .config import Settings
from .evidence import FileEvidenceStore
from .persistence import Database, SqlAlchemyStore
from .plugins import PluginRegistry
from .renewal import SessionRenewalManager

logger = logging.getLogger(__name__)

AUTO_RENEW_SLUGS = frozenset({"bradesco"})


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db = Database(settings.database_url)
        self.evidence = FileEvidenceStore(settings.evidence_dir)
        self.clock = SystemClock(settings.timezone)
        builtin_plugins = Path(corretor.plugins.__file__).resolve().parent
        plugin_dirs = [builtin_plugins, *settings.plugin_path_list]
        self.plugins = PluginRegistry(
            plugin_dirs,
            context=PluginContext(settings=settings.bradesco_context),
        )
        self.renewal = SessionRenewalManager(settings)
        self._scheduler: BackgroundScheduler | None = None

    def init_db(self) -> None:
        self.settings.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.db.create_all()

    def initialize(self) -> None:
        self.init_db()
        if self.settings.seed_demo:
            self.seed_demo()

    @contextmanager
    def session(self) -> Iterator[SqlAlchemyStore]:
        with self.db.session() as session:
            yield SqlAlchemyStore(session)

    def collection_service(self, store: SqlAlchemyStore) -> CollectionService:
        return CollectionService(
            store=store,
            provider=self.plugins,
            evidence=self.evidence,
            clock=self.clock,
        )

    def pendency_service(self, store: SqlAlchemyStore) -> PendencyService:
        return PendencyService(store=store, clock=self.clock)

    def seed_demo(self) -> None:
        with self.session() as store:
            for manifest in self.plugins.manifests():
                if manifest.status != "ready" or manifest.requires_session:
                    continue
                insurer = store.get_insurer_by_slug(manifest.slug)
                if insurer is None:
                    insurer = store.create_insurer(
                        slug=manifest.slug,
                        name=manifest.name,
                        adapter=manifest.slug,
                        active=True,
                    )
                if insurer.last_success_at is None:
                    self.collection_service(store).collect(manifest.slug)

    def _auto_renew_available(self, slug: str) -> bool:
        return slug in AUTO_RENEW_SLUGS and self.renewal.auto_available()

    def _start_auto_renew(self, slug: str) -> bool:
        logger.info("sessão expirada em %s; tentando renovação automática", slug)
        status = self.renewal.start(auto=True, respect_cooldown=True)
        if status.status in {"running", "success"}:
            return True
        logger.warning(
            "renovação automática não iniciada para %s: %s",
            slug,
            status.message,
        )
        return False

    def collect(
        self,
        slug: str,
        *,
        auto_renew: bool = True,
        wait_for_renewal: bool = True,
    ) -> CollectionOutcome:
        with self.session() as store:
            service = self.collection_service(store)
            service.ensure_insurer(slug)
            outcome = service.collect(slug)
        if (
            outcome.status is not RunStatus.NEEDS_ATTENTION
            or not auto_renew
            or not self._auto_renew_available(slug)
        ):
            return outcome
        if wait_for_renewal:
            renewal = self.renewal.auto_renew()
            if renewal.status == "success":
                with self.session() as store:
                    outcome = self.collection_service(store).collect(slug)
            return outcome
        if self._start_auto_renew(slug):
            return replace(outcome, renewal_started=True)
        return outcome

    def collect_all(
        self,
        *,
        auto_renew: bool = True,
        wait_for_renewal: bool = True,
    ) -> list[CollectionOutcome]:
        with self.session() as store:
            outcomes = self.collection_service(store).collect_all()
        if not auto_renew:
            return outcomes
        renewable = [
            outcome
            for outcome in outcomes
            if outcome.status is RunStatus.NEEDS_ATTENTION
            and self._auto_renew_available(outcome.insurer_slug)
        ]
        if not renewable:
            return outcomes
        if wait_for_renewal:
            logger.info("sessão expirada; tentando renovação automática")
            renewal = self.renewal.auto_renew()
            if renewal.status == "success":
                logger.info("sessão renovada automaticamente; repetindo coleta")
                with self.session() as store:
                    outcomes = self.collection_service(store).collect_all()
            else:
                logger.warning("renovação automática não concluída: %s", renewal.message)
            return outcomes
        started: set[str] = set()
        for outcome in renewable:
            if self._start_auto_renew(outcome.insurer_slug):
                started.add(outcome.insurer_slug)
        if not started:
            return outcomes
        return [
            replace(outcome, renewal_started=True) if outcome.insurer_slug in started else outcome
            for outcome in outcomes
        ]

    def mark_overdue(self) -> int:
        with self.session() as store:
            return self.pendency_service(store).mark_overdue()

    def stale_before(self) -> datetime:
        return self.clock.now() - timedelta(hours=self.settings.stale_after_hours)

    def run_daily_job(self) -> None:
        outcomes = self.collect_all()
        overdue = self.mark_overdue()
        successes = sum(1 for outcome in outcomes if outcome.ok)
        logger.info(
            "coleta diária: %s sucesso(s), %s falha(s), %s vencida(s) marcada(s)",
            successes,
            len(outcomes) - successes,
            overdue,
        )

    def start_scheduler(self) -> None:
        if not self.settings.enable_scheduler or self._scheduler is not None:
            return
        timezone = ZoneInfo(self.settings.timezone)
        scheduler = BackgroundScheduler(timezone=timezone)
        scheduler.add_job(
            self.run_daily_job,
            CronTrigger(
                hour=self.settings.scheduler_hour,
                minute=self.settings.scheduler_minute,
                timezone=timezone,
            ),
            id="daily_collection",
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        self._scheduler = scheduler
        logger.info(
            "scheduler ativo: %02d:%02d (%s)",
            self.settings.scheduler_hour,
            self.settings.scheduler_minute,
            self.settings.timezone,
        )

    def shutdown(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
