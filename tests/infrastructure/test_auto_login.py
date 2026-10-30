from __future__ import annotations

from corretor.infrastructure.bradesco_login import is_logged_in_url


def test_url_de_login_com_target_arealogada_nao_e_sucesso() -> None:
    url = (
        "https://login.bradescoseguros.com.br/nidp/app/login"
        "?id=secure_name_pasword_form_pneg"
        "&target=https%3A%2F%2Fwwwn.bradescoseguros.com.br"
        "%2Fpnegocios%2Fwps%2Fmyportal%2Fportalnegocios%2Farealogada%2F"
    )
    assert is_logged_in_url(url) is False


def test_area_logada_e_reconhecida_pelo_path() -> None:
    assert is_logged_in_url(
        "https://wwwn.bradescoseguros.com.br/pnegocios/wps/myportal/portalnegocios/arealogada/"
    )
    assert (
        is_logged_in_url(
            "https://wwwn.bradescoseguros.com.br/pnegocios2/wps/portal/portaldenegociosnovo/"
        )
        is False
    )
    assert is_logged_in_url("https://exemplo.com/arealogada/") is False
