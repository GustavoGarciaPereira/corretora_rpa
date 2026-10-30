from __future__ import annotations

import argparse
import getpass
import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from corretor.infrastructure.config import Settings
from corretor.infrastructure.container import Container
from corretor.infrastructure.credentials import (
    CredentialsError,
    clear_bradesco_credentials,
    resolve_bradesco_credentials,
    store_bradesco_credentials,
)


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _print_outcomes(outcomes) -> None:
    for outcome in outcomes:
        marker = "OK" if outcome.ok else "FALHA"
        print(
            f"[{marker}] {outcome.insurer_name}: {outcome.status.label} "
            f"itens={outcome.items_found} novas={outcome.new_count} "
            f"resolvidas={outcome.resolved_count}"
        )
        if outcome.error:
            print(f"        erro: {outcome.error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="corretor")
    parser.add_argument("--log-level", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="cria as tabelas")
    sub.add_parser("seed", help="cria a seguradora demo e coleta dados fictícios")

    collect = sub.add_parser("collect", help="executa a coleta")
    collect.add_argument("slug", nargs="?", default="all", help="slug da seguradora ou 'all'")

    sub.add_parser("mark-overdue", help="marca pendências abertas vencidas")
    sub.add_parser("plugins", help="lista plugins carregados e erros")
    sub.add_parser("scheduler", help="roda o agendador diário em primeiro plano")

    credentials = sub.add_parser("credentials", help="gerencia credenciais no cofre/keyring")
    credentials.add_argument("action", choices=["set", "status", "clear"])
    credentials.add_argument("portal", choices=["bradesco"])
    return parser


def _credentials(settings: Settings, action: str, portal: str) -> int:
    if portal != "bradesco":
        print("portal não suportado")
        return 2
    try:
        if action == "set":
            if settings.bradesco_credential_source != "keyring":
                print(
                    "aviso: BRADESCO_CREDENTIAL_SOURCE não é 'keyring'; "
                    "o login automático usará as variáveis de ambiente."
                )
            login = input("CNPJ/login da corretora (primeira página): ").strip()
            user = input("CPF do usuário (segunda página; Enter para usar o CNPJ): ").strip()
            password = getpass.getpass("Senha do portal: ")
            confirmation = getpass.getpass("Confirme a senha: ")
            if password != confirmation:
                print("as senhas não conferem")
                return 1
            store_bradesco_credentials(settings, login, user or login, password)
            print("credenciais salvas no keyring")
            return 0
        if action == "status":
            resolve_bradesco_credentials(settings)
            print("credenciais configuradas")
            return 0
        if action == "clear":
            clear_bradesco_credentials(settings)
            print("credenciais removidas")
            return 0
    except CredentialsError as exc:
        print(f"credenciais: {exc}")
        return 1
    return 2


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings()
    _configure_logging(args.log_level or settings.log_level)
    container = Container(settings)

    if args.command == "init-db":
        container.init_db()
        print("banco inicializado")
        return 0

    if args.command == "seed":
        container.init_db()
        container.seed_demo()
        print("seed concluído")
        return 0

    if args.command == "credentials":
        return _credentials(settings, args.action, args.portal)

    if args.command == "plugins":
        for manifest in container.plugins.manifests():
            print(f"{manifest.slug:16} {manifest.status:10} v{manifest.version:8} {manifest.name}")
        for error in container.plugins.errors:
            print(f"[ERRO] {error.path}: {error.error}")
        return 0

    if args.command == "collect":
        container.init_db()
        if args.slug == "all":
            _print_outcomes(container.collect_all())
        else:
            _print_outcomes([container.collect(args.slug)])
        return 0

    if args.command == "mark-overdue":
        container.init_db()
        count = container.mark_overdue()
        print(f"{count} pendência(s) marcada(s) como vencida(s)")
        return 0

    if args.command == "scheduler":
        container.init_db()
        timezone = ZoneInfo(settings.timezone)
        scheduler = BlockingScheduler(timezone=timezone)
        scheduler.add_job(
            container.run_daily_job,
            CronTrigger(
                hour=settings.scheduler_hour,
                minute=settings.scheduler_minute,
                timezone=timezone,
            ),
            id="daily_collection",
            max_instances=1,
            coalesce=True,
        )
        print(
            f"scheduler ativo: {settings.scheduler_hour:02d}:"
            f"{settings.scheduler_minute:02d} ({settings.timezone})"
        )
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown(wait=False)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
