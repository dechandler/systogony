
SSH_AUTH_SOCK="${HOME}/.ssh/sockets/agent.sock"
AGENT_ENV_FILE="${HOME}/.ssh/agent.env"

source "${AGENT_ENV_FILE}" \
    && ps -P ${SSH_AGENT_PID} &>/dev/null \
    && [[ -S "${SSH_AUTH_SOCK}" ]] \
    || {
        rm -f "${SSH_AUTH_SOCK}" "${AGENT_ENV_FILE}"
        /usr/bin/ssh-agent -a "${SSH_AUTH_SOCK}" | head -2 > "${AGENT_ENV_FILE}"
        source "${AGENT_ENV_FILE}"
    }
