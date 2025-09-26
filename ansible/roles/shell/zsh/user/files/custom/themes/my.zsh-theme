

if [[ -n "$SSH_CLIENT" || -n "$SSH_TTY" ]]; then
    local this_path="%{$fg[yellow]%}%~"
else
    local this_path="%{$fg[green]%}%~"
fi

local return_status="%(?:%{$fg_bold[green]%}%(!.#.$)%s:%{$fg_bold[red]%}%(!.#.$)%s)"

PROMPT='${this_path} %{$fg_bold[blue]%}$(git_prompt_info)%{$fg_bold[blue]%}% ${return_status}%{$reset_color%} '


local root_host_info="%{$fg_bold[red]}%m%{$reset_color}"
local unprivileged_host_info="%{$fg[magenta]%}%n%{$fg[blue]%}@%{$fg[yellow]%}%m%{$reset_color%}"
local host_info="%(!.${root_host_info}.${unprivileged_host_info})"

RPROMPT="${host_info}"


ZSH_THEME_GIT_PROMPT_PREFIX="(" #%{$fg[red]%}"
ZSH_THEME_GIT_PROMPT_SUFFIX="%{$reset_color%}"
ZSH_THEME_GIT_PROMPT_DIRTY_PREFIX="%{$fg[red]%}"
ZSH_THEME_GIT_PROMPT_CLEAN_PREFIX="%{$fg[green]%}"
ZSH_THEME_GIT_PROMPT_DIRTY="%{$fg[blue]%}) "  #%{$fg[yellow]%}✗ %{$reset_color%}"
ZSH_THEME_GIT_PROMPT_CLEAN="%{$fg[blue]%}) "
