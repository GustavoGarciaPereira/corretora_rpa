from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime

from corretor.domain.entities import CollectionRun, Insurer
from corretor.domain.enums import RunStatus
from corretor.domain.errors import (
    AdapterError,
    AdapterSessionExpired,
    NotFoundError,
)

from ..dto import CollectionOutcome
from ..logic.diff import compute_diff
from ..logic.normalization import normalize_items
from ..ports import AdapterProvider, EvidenceStore, Store

logger = logging.getLogger(__name__)


class CollectionService:
    def __init__(
        self,
        store: Store,
        provider: AdapterProvider,
        evidence: EvidenceStore,
        clock,
    ) -> None:
        self.store = store
        self.provider = provider
        self.evidence = evidence
        self.clock = clock

    def ensure_insurer(self, slug: str) -> Insurer:
        insurer = self.store.get_insurer_by_slug(slug)
        if insurer is not None:
            return insurer
        manifest = next((m for m in self.provider.manifests() if m.slug == slug), None)
        if manifest is None:
            raise NotFoundError(f"plugin não encontrado: {slug}")
        return self.store.create_insurer(
            slug=manifest.slug,
            name=manifest.name,
            adapter=manifest.slug,
            active=True,
        )

    def collect(self, slug: str) -> CollectionOutcome:
        insurer = self.store.get_insurer_by_slug(slug)
        if insurer is None:
            raise NotFoundError(f"seguradora não cadastrada: {slug}")
        if insurer.id is None:
            raise AdapterError(f"seguradora sem id: {slug}")

        started = self.clock.now()
        run: CollectionRun = self.store.start_run(insurer.id, started)
        if run.id is None:
            raise AdapterError("não foi possível criar a execução de coleta")

        try:
            adapter = self.provider.get(slug)
            raw_items = adapter.fetch_pending()
            items = normalize_items(raw_items)
            evidence_path = self.evidence.save(
                run_id=run.id,
                insurer_slug=slug,
                payload={
                    "raw": [asdict(item) for item in raw_items],
                    "normalized": [asdict(item) for item in items],
                },
            )
            snapshot = self.store.load_snapshot(insurer.id)
            diff = compute_diff(snapshot, items)
            stats = self.store.apply_diff(insurer.id, diff, started)
            finished = self.clock.now()
            self.store.finish_run(
                run_id=run.id,
                status=RunStatus.SUCCESS,
                finished_at=finished,
                items_found=len(items),
                new_count=stats.new_count,
                resolved_count=stats.resolved_count,
                error="",
                evidence_path=evidence_path,
            )
            self.store.set_insurer_run_times(insurer.id, finished, finished)
            return CollectionOutcome(
                insurer_slug=slug,
                insurer_name=insurer.name,
                status=RunStatus.SUCCESS,
                items_found=len(items),
                new_count=stats.new_count,
                resolved_count=stats.resolved_count,
            )
        except AdapterSessionExpired as exc:
            return self._fail(insurer, run, started, exc, RunStatus.NEEDS_ATTENTION)
        except Exception as exc:  # noqa: BLE001 - falha deve ser registrada, não engolida
            logger.exception("falha na coleta de %s", slug)
            return self._fail(insurer, run, started, exc, RunStatus.FAILED)

    def collect_all(self) -> list[CollectionOutcome]:
        outcomes: list[CollectionOutcome] = []
        for insurer in self.store.list_active_insurers():
            try:
                outcomes.append(self.collect(insurer.slug))
            except Exception as exc:  # noqa: BLE001
                logger.exception("falha ao coletar %s", insurer.slug)
                outcomes.append(
                    CollectionOutcome(
                        insurer_slug=insurer.slug,
                        insurer_name=insurer.name,
                        status=RunStatus.FAILED,
                        error=str(exc),
                    )
                )
        return outcomes

    def _fail(
        self,
        insurer: Insurer,
        run: CollectionRun,
        started: datetime,
        exc: Exception,
        status: RunStatus,
    ) -> CollectionOutcome:
        finished = self.clock.now()
        error = str(exc) or exc.__class__.__name__
        evidence_path = ""
        if run.id is not None:
            try:
                evidence_path = self.evidence.save(
                    run_id=run.id,
                    insurer_slug=insurer.slug,
                    payload={"error": error, "error_type": exc.__class__.__name__},
                    error=error,
                )
            except Exception:  # noqa: BLE001 - evidência não pode esconder a falha original
                logger.exception("falha ao salvar evidência de %s", insurer.slug)
            self.store.finish_run(
                run_id=run.id,
                status=status,
                finished_at=finished,
                items_found=0,
                new_count=0,
                resolved_count=0,
                error=error,
                evidence_path=evidence_path,
            )
        if insurer.id is not None:
            self.store.set_insurer_run_times(insurer.id, started, None)
        return CollectionOutcome(
            insurer_slug=insurer.slug,
            insurer_name=insurer.name,
            status=status,
            error=error,
        )
