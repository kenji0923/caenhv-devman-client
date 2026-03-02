from __future__ import annotations

import itertools
import os
import re
from typing import Any

from .runtime.client import ManagerClient

try:
    from caen_libs.caenhvwrapper import *
    from collections.abc import *
except Exception:
    from enum import Enum, IntEnum

    class Device:
        pass

    class Error:
        pass

    class Sequence:
        pass

_PARAM_ORDER = { 'Device_get_bd_param': ['slot_list', 'name'],
  'Device_get_bd_param_info': ['slot'],
  'Device_get_bd_param_prop': ['slot', 'name'],
  'Device_get_ch_name': ['slot', 'channel_list'],
  'Device_get_ch_param': ['slot', 'channel_list', 'name'],
  'Device_get_ch_param_info': ['slot', 'channel'],
  'Device_get_ch_param_prop': ['slot', 'channel', 'name'],
  'Device_get_crate_map': [],
  'Device_get_event_data': [],
  'Device_get_events_tcp_ports': [],
  'Device_get_exec_comm_list': [],
  'Device_get_sys_prop': ['name'],
  'Device_get_sys_prop_info': ['name'],
  'Device_get_sys_prop_list': [],
  'Device_set_ch_name': ['slot', 'channel_list', 'name'],
  'Device_set_ch_param': ['slot', 'channel_list', 'name', 'value'],
  'Device_test_bd_presence': ['slot'],
  'Error_Code': ['values']}
_PARAM_KINDS = { 'Device_get_bd_param': { 'name': 'POSITIONAL_OR_KEYWORD',
                           'slot_list': 'POSITIONAL_OR_KEYWORD'},
  'Device_get_bd_param_info': {'slot': 'POSITIONAL_OR_KEYWORD'},
  'Device_get_bd_param_prop': { 'name': 'POSITIONAL_OR_KEYWORD',
                                'slot': 'POSITIONAL_OR_KEYWORD'},
  'Device_get_ch_name': { 'channel_list': 'POSITIONAL_OR_KEYWORD',
                          'slot': 'POSITIONAL_OR_KEYWORD'},
  'Device_get_ch_param': { 'channel_list': 'POSITIONAL_OR_KEYWORD',
                           'name': 'POSITIONAL_OR_KEYWORD',
                           'slot': 'POSITIONAL_OR_KEYWORD'},
  'Device_get_ch_param_info': { 'channel': 'POSITIONAL_OR_KEYWORD',
                                'slot': 'POSITIONAL_OR_KEYWORD'},
  'Device_get_ch_param_prop': { 'channel': 'POSITIONAL_OR_KEYWORD',
                                'name': 'POSITIONAL_OR_KEYWORD',
                                'slot': 'POSITIONAL_OR_KEYWORD'},
  'Device_get_crate_map': {},
  'Device_get_event_data': {},
  'Device_get_events_tcp_ports': {},
  'Device_get_exec_comm_list': {},
  'Device_get_sys_prop': {'name': 'POSITIONAL_OR_KEYWORD'},
  'Device_get_sys_prop_info': {'name': 'POSITIONAL_OR_KEYWORD'},
  'Device_get_sys_prop_list': {},
  'Device_set_ch_name': { 'channel_list': 'POSITIONAL_OR_KEYWORD',
                          'name': 'POSITIONAL_OR_KEYWORD',
                          'slot': 'POSITIONAL_OR_KEYWORD'},
  'Device_set_ch_param': { 'channel_list': 'POSITIONAL_OR_KEYWORD',
                           'name': 'POSITIONAL_OR_KEYWORD',
                           'slot': 'POSITIONAL_OR_KEYWORD',
                           'value': 'POSITIONAL_OR_KEYWORD'},
  'Device_test_bd_presence': {'slot': 'POSITIONAL_OR_KEYWORD'},
  'Error_Code': {'values': 'VAR_POSITIONAL'}}
_RESOURCE_TEMPLATES = { 'Device_get_bd_param': None,
  'Device_get_bd_param_info': None,
  'Device_get_bd_param_prop': None,
  'Device_get_ch_name': None,
  'Device_get_ch_param': None,
  'Device_get_ch_param_info': None,
  'Device_get_ch_param_prop': None,
  'Device_get_crate_map': None,
  'Device_get_event_data': None,
  'Device_get_events_tcp_ports': None,
  'Device_get_exec_comm_list': None,
  'Device_get_sys_prop': None,
  'Device_get_sys_prop_info': None,
  'Device_get_sys_prop_list': None,
  'Device_set_ch_name': 'slot:{slot}:ch:{channel_list[]}',
  'Device_set_ch_param': 'slot:{slot}:ch:{channel_list[]}',
  'Device_test_bd_presence': None,
  'Error_Code': None}

def _default_client_name() -> str:
    name = os.getenv('DEVMAN_CLIENT')
    if name is None or not str(name).strip():
        raise RuntimeError('DEVMAN_CLIENT is required')
    return str(name).strip()

_CLIENT = ManagerClient(
    host=os.getenv('DEVMAN_HOST', '127.0.0.1'),
    port=int(os.getenv('DEVMAN_PORT', '50250')),
    client_name=_default_client_name(),
)

def configure_connection(host: str, port: int, client_name: str, timeout: float = 5.0) -> None:
    global _CLIENT
    _CLIENT = ManagerClient(host=host, port=port, client_name=client_name, timeout=timeout)

def acquire(resource: str) -> bool:
    return _CLIENT.acquire(resource)

def release(resource: str) -> bool:
    return _CLIENT.release(resource)

def owner_of(resource: str) -> str | None:
    return _CLIENT.owner_of(resource)

def owners_of(resources: list[str]) -> dict[str, str | None]:
    return _CLIENT.owners_of(resources)

def connect(force: bool = False) -> None:
    _CLIENT.connect(force=force)

def disconnect() -> None:
    _CLIENT.disconnect()

def close() -> None:
    _CLIENT.close()

_EXPAND_FIELD_RE = re.compile(r'\{([A-Za-z_]\w*)\[\]\}')

def _expand_resource_template(template: str, context: dict[str, Any]) -> list[str]:
    expand_fields = _EXPAND_FIELD_RE.findall(template)
    if not expand_fields:
        return [template.format(**context)]
    ordered_fields = list(dict.fromkeys(expand_fields))
    normalized = template
    values_by_field: list[list[Any]] = []
    for field in ordered_fields:
        normalized = normalized.replace(f'{{{field}[]}}', f'{{{field}}}')
        raw = context.get(field)
        if raw is None:
            return []
        if isinstance(raw, (str, bytes, bytearray)):
            values = [raw]
        else:
            try:
                values = list(raw)
            except TypeError:
                values = [raw]
        if not values:
            return []
        values_by_field.append(values)
    resources: list[str] = []
    for combo in itertools.product(*values_by_field):
        local_context = dict(context)
        for field, value in zip(ordered_fields, combo):
            local_context[field] = value
        resources.append(normalized.format(**local_context))
    return resources

def _pack_call_args(function: str, local_vars: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
    order = _PARAM_ORDER[function]
    kinds = _PARAM_KINDS[function]
    args: list[Any] = []
    kwargs: dict[str, Any] = {}
    for name in order:
        if name not in local_vars or name in ('self', 'cls'):
            continue
        kind = kinds.get(name, 'POSITIONAL_OR_KEYWORD')
        value = local_vars[name]
        if kind == 'VAR_POSITIONAL':
            args.extend(list(value))
        elif kind == 'VAR_KEYWORD':
            kwargs.update(dict(value))
        elif kind == 'KEYWORD_ONLY':
            kwargs[name] = value
        else:
            args.append(value)
    return args, kwargs

def _resources_for(function: str, local_vars: dict[str, Any]) -> list[str]:
    context = dict(local_vars)
    context.pop('kwargs', None)
    template = _RESOURCE_TEMPLATES.get(function)
    if not template:
        return []
    return _expand_resource_template(template, context)

def Device_get_bd_param(slot_list: collections.abc.Sequence[int], name: str):
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_bd_param', _locals)
    _resources = _resources_for('Device_get_bd_param', _locals)
    return _CLIENT.invoke('Device_get_bd_param', _args, _kwargs, _resources)

def Device_get_bd_param_info(slot: int):
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_bd_param_info', _locals)
    _resources = _resources_for('Device_get_bd_param_info', _locals)
    return _CLIENT.invoke('Device_get_bd_param_info', _args, _kwargs, _resources)

def Device_get_bd_param_prop(slot: int, name: str):
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_bd_param_prop', _locals)
    _resources = _resources_for('Device_get_bd_param_prop', _locals)
    return _CLIENT.invoke('Device_get_bd_param_prop', _args, _kwargs, _resources)

def Device_get_ch_name(slot: int, channel_list: collections.abc.Sequence[int]):
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_ch_name', _locals)
    _resources = _resources_for('Device_get_ch_name', _locals)
    return _CLIENT.invoke('Device_get_ch_name', _args, _kwargs, _resources)

def Device_get_ch_param(slot: int, channel_list: collections.abc.Sequence[int], name: str):
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_ch_param', _locals)
    _resources = _resources_for('Device_get_ch_param', _locals)
    return _CLIENT.invoke('Device_get_ch_param', _args, _kwargs, _resources)

def Device_get_ch_param_info(slot: int, channel: int):
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_ch_param_info', _locals)
    _resources = _resources_for('Device_get_ch_param_info', _locals)
    return _CLIENT.invoke('Device_get_ch_param_info', _args, _kwargs, _resources)

def Device_get_ch_param_prop(slot: int, channel: int, name: str):
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_ch_param_prop', _locals)
    _resources = _resources_for('Device_get_ch_param_prop', _locals)
    return _CLIENT.invoke('Device_get_ch_param_prop', _args, _kwargs, _resources)

def Device_get_crate_map():
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_crate_map', _locals)
    _resources = _resources_for('Device_get_crate_map', _locals)
    return _CLIENT.invoke('Device_get_crate_map', _args, _kwargs, _resources)

def Device_get_event_data():
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_event_data', _locals)
    _resources = _resources_for('Device_get_event_data', _locals)
    return _CLIENT.invoke('Device_get_event_data', _args, _kwargs, _resources)

def Device_get_events_tcp_ports():
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_events_tcp_ports', _locals)
    _resources = _resources_for('Device_get_events_tcp_ports', _locals)
    return _CLIENT.invoke('Device_get_events_tcp_ports', _args, _kwargs, _resources)

def Device_get_exec_comm_list():
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_exec_comm_list', _locals)
    _resources = _resources_for('Device_get_exec_comm_list', _locals)
    return _CLIENT.invoke('Device_get_exec_comm_list', _args, _kwargs, _resources)

def Device_get_sys_prop(name: str):
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_sys_prop', _locals)
    _resources = _resources_for('Device_get_sys_prop', _locals)
    return _CLIENT.invoke('Device_get_sys_prop', _args, _kwargs, _resources)

def Device_get_sys_prop_info(name: str):
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_sys_prop_info', _locals)
    _resources = _resources_for('Device_get_sys_prop_info', _locals)
    return _CLIENT.invoke('Device_get_sys_prop_info', _args, _kwargs, _resources)

def Device_get_sys_prop_list():
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_get_sys_prop_list', _locals)
    _resources = _resources_for('Device_get_sys_prop_list', _locals)
    return _CLIENT.invoke('Device_get_sys_prop_list', _args, _kwargs, _resources)

def Device_set_ch_name(slot: int, channel_list: collections.abc.Sequence[int], name: str):
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_set_ch_name', _locals)
    _resources = _resources_for('Device_set_ch_name', _locals)
    return _CLIENT.invoke('Device_set_ch_name', _args, _kwargs, _resources)

def Device_set_ch_param(slot: int, channel_list: collections.abc.Sequence[int], name: str, value: str | float | int | None):
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_set_ch_param', _locals)
    _resources = _resources_for('Device_set_ch_param', _locals)
    return _CLIENT.invoke('Device_set_ch_param', _args, _kwargs, _resources)

def Device_test_bd_presence(slot: int):
    _locals = locals()
    _args, _kwargs = _pack_call_args('Device_test_bd_presence', _locals)
    _resources = _resources_for('Device_test_bd_presence', _locals)
    return _CLIENT.invoke('Device_test_bd_presence', _args, _kwargs, _resources)

def Error_Code(*values):
    _locals = locals()
    _args, _kwargs = _pack_call_args('Error_Code', _locals)
    _resources = _resources_for('Error_Code', _locals)
    return _CLIENT.invoke('Error_Code', _args, _kwargs, _resources)

class Device:
    def __init__(self, handle: str) -> None:
        self._handle = handle

    def get_bd_param(self, slot_list: collections.abc.Sequence[int], name: str):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_bd_param', _locals)
        _resources = _resources_for('Device_get_bd_param', _locals)
        return _CLIENT.invoke('Device_get_bd_param', _args, _kwargs, _resources, handle=self._handle)

    def get_bd_param_info(self, slot: int):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_bd_param_info', _locals)
        _resources = _resources_for('Device_get_bd_param_info', _locals)
        return _CLIENT.invoke('Device_get_bd_param_info', _args, _kwargs, _resources, handle=self._handle)

    def get_bd_param_prop(self, slot: int, name: str):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_bd_param_prop', _locals)
        _resources = _resources_for('Device_get_bd_param_prop', _locals)
        return _CLIENT.invoke('Device_get_bd_param_prop', _args, _kwargs, _resources, handle=self._handle)

    def get_ch_name(self, slot: int, channel_list: collections.abc.Sequence[int]):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_ch_name', _locals)
        _resources = _resources_for('Device_get_ch_name', _locals)
        return _CLIENT.invoke('Device_get_ch_name', _args, _kwargs, _resources, handle=self._handle)

    def get_ch_param(self, slot: int, channel_list: collections.abc.Sequence[int], name: str):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_ch_param', _locals)
        _resources = _resources_for('Device_get_ch_param', _locals)
        return _CLIENT.invoke('Device_get_ch_param', _args, _kwargs, _resources, handle=self._handle)

    def get_ch_param_info(self, slot: int, channel: int):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_ch_param_info', _locals)
        _resources = _resources_for('Device_get_ch_param_info', _locals)
        return _CLIENT.invoke('Device_get_ch_param_info', _args, _kwargs, _resources, handle=self._handle)

    def get_ch_param_prop(self, slot: int, channel: int, name: str):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_ch_param_prop', _locals)
        _resources = _resources_for('Device_get_ch_param_prop', _locals)
        return _CLIENT.invoke('Device_get_ch_param_prop', _args, _kwargs, _resources, handle=self._handle)

    def get_crate_map(self):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_crate_map', _locals)
        _resources = _resources_for('Device_get_crate_map', _locals)
        return _CLIENT.invoke('Device_get_crate_map', _args, _kwargs, _resources, handle=self._handle)

    def get_event_data(self):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_event_data', _locals)
        _resources = _resources_for('Device_get_event_data', _locals)
        return _CLIENT.invoke('Device_get_event_data', _args, _kwargs, _resources, handle=self._handle)

    def get_events_tcp_ports(self):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_events_tcp_ports', _locals)
        _resources = _resources_for('Device_get_events_tcp_ports', _locals)
        return _CLIENT.invoke('Device_get_events_tcp_ports', _args, _kwargs, _resources, handle=self._handle)

    def get_exec_comm_list(self):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_exec_comm_list', _locals)
        _resources = _resources_for('Device_get_exec_comm_list', _locals)
        return _CLIENT.invoke('Device_get_exec_comm_list', _args, _kwargs, _resources, handle=self._handle)

    def get_sys_prop(self, name: str):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_sys_prop', _locals)
        _resources = _resources_for('Device_get_sys_prop', _locals)
        return _CLIENT.invoke('Device_get_sys_prop', _args, _kwargs, _resources, handle=self._handle)

    def get_sys_prop_info(self, name: str):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_sys_prop_info', _locals)
        _resources = _resources_for('Device_get_sys_prop_info', _locals)
        return _CLIENT.invoke('Device_get_sys_prop_info', _args, _kwargs, _resources, handle=self._handle)

    def get_sys_prop_list(self):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_get_sys_prop_list', _locals)
        _resources = _resources_for('Device_get_sys_prop_list', _locals)
        return _CLIENT.invoke('Device_get_sys_prop_list', _args, _kwargs, _resources, handle=self._handle)

    def set_ch_name(self, slot: int, channel_list: collections.abc.Sequence[int], name: str):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_set_ch_name', _locals)
        _resources = _resources_for('Device_set_ch_name', _locals)
        return _CLIENT.invoke('Device_set_ch_name', _args, _kwargs, _resources, handle=self._handle)

    def set_ch_param(self, slot: int, channel_list: collections.abc.Sequence[int], name: str, value: str | float | int | None):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_set_ch_param', _locals)
        _resources = _resources_for('Device_set_ch_param', _locals)
        return _CLIENT.invoke('Device_set_ch_param', _args, _kwargs, _resources, handle=self._handle)

    def test_bd_presence(self, slot: int):
        _locals = locals()
        _args, _kwargs = _pack_call_args('Device_test_bd_presence', _locals)
        _resources = _resources_for('Device_test_bd_presence', _locals)
        return _CLIENT.invoke('Device_test_bd_presence', _args, _kwargs, _resources, handle=self._handle)
