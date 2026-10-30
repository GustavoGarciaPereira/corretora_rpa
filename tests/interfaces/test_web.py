from __future__ import annotations

from fastapi.testclient import TestClient

from corretor.application.dto import CollectionOutcome, PendencyFilters
from corretor.domain.enums import RunStatus, WorkflowStatus
from corretor.interfaces.web.app import create_app


def test_painel_coleta_e_workflow(settings) -> None:
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.container.seed_demo()

        home = client.get("/")
        assert home.status_code == 200
        assert "Parcelas pendentes" in home.text
        assert "Seguradora Demo" in home.text

        partial = client.get("/dashboard?status=ABERTAS")
        assert partial.status_code == 200
        assert "Pendências" in partial.text

        plugins = client.get("/plugins")
        assert plugins.status_code == 200
        assert "Seguradora Demo" in plugins.text
        assert "Bradesco Seguros" in plugins.text

        runs = client.get("/runs")
        assert runs.status_code == 200
        assert "Execuções de coleta" in runs.text

        sessions = client.get("/sessions")
        assert sessions.status_code == 200
        assert "Sessões dos portais" in sessions.text
        assert "Seguradora Demo" in sessions.text

        health = client.get("/healthz")
        assert health.status_code == 200
        assert health.json()["database"] is True

        collect = client.post("/collect")
        assert collect.status_code == 200
        assert "Coleta concluída" in collect.text

        container = app.state.container
        with container.session() as store:
            views = store.list_pendencies(PendencyFilters(), container.clock.today())
            pendency_id = views[0].id

        status_response = client.post(
            f"/pendencies/{pendency_id}/status",
            data={"workflow_status": WorkflowStatus.EM_ANALISE.value},
        )
        assert status_response.status_code == 200
        with container.session() as store:
            detail = store.get_pendency_detail(pendency_id, container.clock.today())
            assert detail is not None
            assert detail.view.workflow_status is WorkflowStatus.EM_ANALISE

        update = client.post(
            f"/pendencies/{pendency_id}",
            data={
                "workflow_status": WorkflowStatus.AVISADA.value,
                "action": "Enviar parcelas até dia 25",
                "new_due_date": "2026-12-10",
                "deadline": "2026-12-05",
                "assigned_to": "Beto",
                "notes": "Cliente avisado",
            },
            follow_redirects=False,
        )
        assert update.status_code == 303

        detail_page = client.get(f"/pendencies/{pendency_id}?saved=1")
        assert detail_page.status_code == 200
        assert "Cliente avisado" in detail_page.text

        csv_response = client.get("/export.csv")
        assert csv_response.status_code == 200
        assert "text/csv" in csv_response.headers["content-type"]
        assert "Seguradora" in csv_response.text

        planilha = client.get("/planilha")
        assert planilha.status_code == 200
        assert "Controle de parcelas pendentes" in planilha.text
        assert "PENDENTE" in planilha.text

        planilha_csv = client.get("/export-planilha.csv")
        assert planilha_csv.status_code == 200
        assert "DATA AÇÃO" in planilha_csv.text
        assert "PENDENTE" in planilha_csv.text

        assert client.get("/pendencies/999999").status_code == 404


def test_modal_de_sessao_expirada(settings, monkeypatch) -> None:
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.container.seed_demo()

        class FakeCollectionService:
            def collect_all(self):
                return [
                    CollectionOutcome(
                        insurer_slug="bradesco",
                        insurer_name="Bradesco Seguros",
                        status=RunStatus.NEEDS_ATTENTION,
                        error="sessão do Bradesco expirada",
                    )
                ]

        monkeypatch.setattr(
            app.state.container,
            "collection_service",
            lambda store: FakeCollectionService(),
        )
        response = client.post("/collect")
        assert response.status_code == 200
        assert "Sessão expirada" in response.text
        assert "Bradesco Seguros" in response.text
        assert "Renovar sessão" in response.text
