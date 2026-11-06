from __future__ import annotations

from fastapi.testclient import TestClient

from corretor.application.dto import CollectionOutcome, PendencyFilters
from corretor.domain.enums import RunStatus, WorkflowStatus
from corretor.interfaces.web.app import create_app


def test_painel_coleta_e_workflow(settings) -> None:
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.container.seed_demo()
        with app.state.container.session() as store:
            store.create_insurer("bradesco", "Bradesco Seguros", "bradesco")

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
        assert "Coletas" in runs.text

        sessions = client.get("/sessions")
        assert sessions.status_code == 200
        assert "Conexões" in sessions.text
        assert "Seguradora Demo" in sessions.text
        assert "Renovar manualmente" in sessions.text

        health = client.get("/healthz")
        assert health.status_code == 200
        assert health.json()["database"] is True

        health_alias = client.get("/health")
        assert health_alias.status_code == 200
        assert health_alias.json()["database"] is True

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


def test_renovacao_mostra_status_de_espera(settings, monkeypatch) -> None:
    from corretor.infrastructure.renewal import RenewalStatus

    app = create_app(settings)
    with TestClient(app) as client:
        monkeypatch.setattr(
            app.state.container.renewal,
            "start",
            lambda: RenewalStatus("running", "navegador aberto"),
        )
        monkeypatch.setattr(
            app.state.container.renewal,
            "status",
            lambda: RenewalStatus("running", "navegador aberto"),
        )
        response = client.post("/sessions/bradesco/renew")
        assert response.status_code == 200
        assert "Renovação em andamento" in response.text
        assert "Aguardando login" in response.text


def test_forcar_expiracao_remove_sessao_salva(settings) -> None:
    app = create_app(settings)
    settings.bradesco_state_path.write_text("{}", encoding="utf-8")

    with TestClient(app) as client:
        with app.state.container.session() as store:
            store.create_insurer("bradesco", "Bradesco Seguros", "bradesco")
        app.state.container.renewal.result_path.write_text("{}", encoding="utf-8")

        response = client.post("/sessions/bradesco/expire", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/sessions?expired=1"
        assert not settings.bradesco_state_path.exists()
        assert not app.state.container.renewal.result_path.exists()

        page = client.get("/sessions?expired=1")
        assert page.status_code == 200
        assert "Conexão forçada a expirar" in page.text
        assert "não encontrada" in page.text
        assert "expirada" in page.text


def test_modal_de_sessao_expirada(settings, monkeypatch) -> None:
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.container.seed_demo()

        monkeypatch.setattr(
            app.state.container,
            "collect_all",
            lambda: [
                CollectionOutcome(
                    insurer_slug="bradesco",
                    insurer_name="Bradesco Seguros",
                    status=RunStatus.NEEDS_ATTENTION,
                    error="sessão do Bradesco expirada",
                )
            ],
        )
        response = client.post("/collect")
        assert response.status_code == 200
        assert "Sessão expirada" in response.text
        assert "Bradesco Seguros" in response.text
        assert "Renovar conexão" in response.text


def test_painel_exibe_erro_completo_e_persistente(settings, monkeypatch) -> None:
    from corretor.domain.errors import AdapterError

    long_error = (
        "Timeout de 60000ms aguardando a tabela de parcelas na pagina do portal; "
        "verifique VPN, sessao do portal e possivel mudanca de layout"
    )

    app = create_app(settings)
    with TestClient(app) as client:
        container = app.state.container
        container.seed_demo()

        class BrokenAdapter:
            def fetch_pending(self):
                raise AdapterError(long_error)

        monkeypatch.setattr(container.plugins, "get", lambda slug: BrokenAdapter())

        collected = client.post("/collect")
        assert collected.status_code == 200
        assert "Precisa de atenção" in collected.text
        assert long_error in collected.text
        assert "pill failed" in collected.text
        assert "Detalhes abaixo" in collected.text

        home = client.get("/")
        assert home.status_code == 200
        assert "Precisa de atenção" in home.text
        assert long_error in home.text
        assert "pill failed" in home.text

        runs = client.get("/runs")
        assert runs.status_code == 200
        assert long_error in runs.text

        sessions = client.get("/sessions")
        assert sessions.status_code == 200
        assert long_error in sessions.text


def test_card_e_painel_compartilham_o_mesmo_estado(settings, monkeypatch) -> None:
    from corretor.domain.errors import AdapterError

    app = create_app(settings)
    with TestClient(app) as client:
        container = app.state.container
        container.seed_demo()
        with container.session() as store:
            store.create_insurer("sem-coleta", "Seguradora Sem Coleta", "demo")

        class BrokenAdapter:
            def fetch_pending(self):
                raise AdapterError("portal indisponível")

        monkeypatch.setattr(container.plugins, "get", lambda slug: BrokenAdapter())
        collected = client.post("/collect/demo")
        assert collected.status_code == 200

        home = client.get("/")
        assert home.status_code == 200
        assert "Seguradoras com atenção · de 2" in home.text
        assert home.text.count('class="error-item"') == 2
        assert "1 falha(s)" in home.text
        assert "1 sem coleta" in home.text
        assert "Seguradora Sem Coleta" in home.text
        assert "Coletar agora" in home.text


def test_filtro_padrao_mostra_abertas_e_permite_historico(settings) -> None:
    app = create_app(settings)
    with TestClient(app) as client:
        container = app.state.container
        container.seed_demo()
        with container.session() as store:
            target = store.list_pendencies(PendencyFilters(), container.clock.today())[0]
            container.pendency_service(store).update_status(target.id, WorkflowStatus.REGULARIZADA)

        home = client.get("/")
        assert home.status_code == 200
        assert "4 registro(s)" in home.text
        assert 'href="/?insurer=demo"' in home.text
        assert "Limpar filtros" not in home.text

        closed = client.get("/?status=REGULARIZADA")
        assert closed.status_code == 200
        assert "1 registro(s)" in closed.text
        assert "Limpar filtros" in closed.text

        everything = client.get("/?status=")
        assert "5 registro(s)" in everything.text


def test_filtro_htmx_atualiza_url_e_recarrega_pagina_completa(settings) -> None:
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.container.seed_demo()

        full = client.get("/?status=ABERTAS")
        assert full.status_code == 200
        assert "<html" in full.text

        partial = client.get("/?status=ABERTAS", headers={"HX-Request": "true"})
        assert partial.status_code == 200
        assert "<html" not in partial.text
        assert "Pendências" in partial.text


def test_coletar_uma_seguradora(settings) -> None:
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.container.seed_demo()

        response = client.post("/collect/demo")
        assert response.status_code == 200
        assert "Coleta concluída: Seguradora Demo." in response.text

        missing = client.post("/collect/inexistente")
        assert missing.status_code == 404
