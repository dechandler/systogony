
```
- name: >
    service/prometheus
    : setup
    : Setup prometheus as rootless podman service
  include_role:
    name: podman-rootless/service
    tasks_from: setup
  vars:
    SVC: "{{ _prom_svc }}"
```

## Keys to provide in SVC parameter

#### name

name of the systemd service used to manage the container

#### user

name of the user to own the systemd service running rootless podman

#### subdirs

subdirectories to create under the rootless user's home directory

#### role

the role containing the config tempates (likely the one calling this role)

#### config_templates

list of template files in {{ role path }}/templates/{{ this }} to be templated into the service's home directory

if the source and destination are different, you can use a syntax of
{{ template path relative to template dir}}:{{ destination path relative to service home}}


#### description

service description for the systemd service

#### keep_uid

boolean to use the `--userns=keep-id` argument to `podman run`

#### network

used with the `--network` argument to `podman run` in the format `podman run --network={{ this }}`

optional, mainly used for defining `--network=host`

#### ports

list of dictionaries
dictionary keys: host_port, container_port

defines ports to be used with the `-p` argument to `podman run` in the format `podman run -p {{ host_port }}:{{ container_port }}`

#### volumes

list of dictionaries
dictionary keys: host_path, container_path, options

defines volumes to be used with the `-v` argument to `podman run` in the format `podman run -v {{ host_path }}:{{ container_path }}:{{ options }}`

options is optional and defaults to `z`


#### image

container image source


#### container_args

string appended to the `podman run` command as arguments to the container
