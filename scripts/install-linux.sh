#!/usr/bin/env bash

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
readonly VENV_DIR="${PROJECT_DIR}/.venv"
readonly LAUNCHER_DIR="${XDG_BIN_HOME:-${HOME}/.local/bin}"
readonly LAUNCHER_PATH="${LAUNCHER_DIR}/impr"
readonly LAUNCHER_MARKER="# impr-managed-launcher: install-linux.sh"

dev_install=false
action="install"
temporary_launcher=""

cleanup() {
    if [[ -n "${temporary_launcher}" ]]; then
        rm -f -- "${temporary_launcher}"
    fi
}
trap cleanup EXIT

usage() {
    cat <<'USAGE'
Uso: scripts/install-linux.sh [opções]

Prepara a instalação do impr no escopo do usuário.

Opções:
  --dev        instala também as dependências de desenvolvimento
  --update     atualiza a instalação existente de forma idempotente
  --uninstall  remove somente o launcher gerenciado em ~/.local/bin/impr
  -h, --help   exibe esta ajuda
USAGE
}

fail() {
    printf 'Erro: %s\n' "$1" >&2
    exit 1
}

parse_args() {
    while (($# > 0)); do
        case "$1" in
            --dev)
                dev_install=true
                ;;
            --update)
                action="install"
                ;;
            --uninstall)
                action="uninstall"
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                usage >&2
                fail "opção desconhecida: $1"
                ;;
        esac
        shift
    done

    if [[ "${action}" == "uninstall" && "${dev_install}" == true ]]; then
        fail "--dev não pode ser combinado com --uninstall"
    fi
}

uninstall_launcher() {
    if [[ ! -e "${LAUNCHER_PATH}" && ! -L "${LAUNCHER_PATH}" ]]; then
        printf 'Launcher não encontrado: %s\n' "${LAUNCHER_PATH}"
        return 0
    fi

    if [[ -L "${LAUNCHER_PATH}" || ! -f "${LAUNCHER_PATH}" ]]; then
        fail "não vou remover um launcher que não seja um arquivo gerenciado: ${LAUNCHER_PATH}"
    fi

    if ! grep -Fqx "${LAUNCHER_MARKER}" "${LAUNCHER_PATH}"; then
        fail "${LAUNCHER_PATH} não foi criado por este instalador; remova-o manualmente se necessário"
    fi

    rm -- "${LAUNCHER_PATH}"
    printf 'Launcher removido: %s\n' "${LAUNCHER_PATH}"
}

require_python() {
    if ! command -v python3 >/dev/null 2>&1; then
        fail "python3 não foi encontrado no PATH"
    fi

    if ! python3 -c 'import venv' >/dev/null 2>&1; then
        fail "o módulo venv não está disponível; instale o pré-requisito do Python na sua distribuição e tente novamente"
    fi
}

prepare_venv() {
    if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
        printf '[+] Criando ambiente virtual em %s\n' "${VENV_DIR}"
        if ! python3 -m venv "${VENV_DIR}"; then
            fail "não foi possível criar ${VENV_DIR}; confirme se o suporte a venv está instalado"
        fi
    else
        printf '[+] Reutilizando ambiente virtual em %s\n' "${VENV_DIR}"
    fi

    readonly VENV_PYTHON="${VENV_DIR}/bin/python"
    if ! "${VENV_PYTHON}" -m pip --version >/dev/null 2>&1; then
        printf '[+] pip não foi encontrado na venv; tentando habilitar o ensurepip\n'
        if ! "${VENV_PYTHON}" -m ensurepip --upgrade >/dev/null 2>&1; then
            fail "pip não está disponível na venv; instale o suporte do Python para venv e tente novamente"
        fi
    fi
}

install_requirements() {
    local requirements_file="${PROJECT_DIR}/requirements.txt"

    if [[ "${dev_install}" == true ]]; then
        requirements_file="${PROJECT_DIR}/requirements-dev.txt"
    fi

    printf '[+] Instalando dependências de %s\n' "${requirements_file}"
    "${VENV_PYTHON}" -m pip install --upgrade -r "${requirements_file}"
}

create_launcher() {
    mkdir -p -- "${LAUNCHER_DIR}"

    if [[ -e "${LAUNCHER_PATH}" || -L "${LAUNCHER_PATH}" ]]; then
        if [[ -L "${LAUNCHER_PATH}" || ! -f "${LAUNCHER_PATH}" ]]; then
            fail "não vou sobrescrever um arquivo que não seja um launcher regular: ${LAUNCHER_PATH}"
        fi
        if ! grep -Fqx "${LAUNCHER_MARKER}" "${LAUNCHER_PATH}"; then
            fail "${LAUNCHER_PATH} já existe e não foi criado por este instalador"
        fi
    fi

    temporary_launcher="$(mktemp "${LAUNCHER_DIR}/.impr-launcher.XXXXXX")"
    {
        printf '%s\n' '#!/usr/bin/env bash' 'set -Eeuo pipefail' "${LAUNCHER_MARKER}"
        printf 'exec %q %q "$@"\n' \
            "${VENV_PYTHON}" \
            "${PROJECT_DIR}/epub_to_print_pdf.py"
    } > "${temporary_launcher}"
    chmod 755 -- "${temporary_launcher}"
    mv -f -- "${temporary_launcher}" "${LAUNCHER_PATH}"
    temporary_launcher=""
}

create_data_directories() {
    mkdir -p -- "${PROJECT_DIR}/epub" "${PROJECT_DIR}/pdf"
}

print_next_steps() {
    printf '\n[+] Instalação concluída.\n'
    printf '    Launcher: %s\n' "${LAUNCHER_PATH}"
    printf '    Ambiente: %s\n' "${VENV_DIR}"

    if [[ ":${PATH:-}:" != *":${LAUNCHER_DIR}:"* ]]; then
        printf '\nAviso: %s não está no PATH desta sessão.\n' "${LAUNCHER_DIR}"
        printf 'Adicione-o ao perfil do seu shell ou abra um terminal que já o inclua:\n'
        printf '  export PATH="%s:$PATH"\n' "${LAUNCHER_DIR}"
    fi

    printf '\nO navegador Chromium é uma dependência externa e não é instalado automaticamente.\n'
    printf 'Use `impr --check` para verificar o ambiente antes da primeira conversão.\n'
}

install_project() {
    require_python
    prepare_venv
    install_requirements
    create_data_directories
    create_launcher
    print_next_steps
}

main() {
    parse_args "$@"

    if [[ "${action}" == "uninstall" ]]; then
        uninstall_launcher
        exit 0
    fi

    install_project
}

main "$@"
