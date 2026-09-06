from __future__ import annotations

from typing import Any, Callable

from .ast_nodes import Command
from .data_mutation_execution import DataMutationExecutionResult, execute_data_mutation
from .data_mutation_semantics import ResolvedDataBinding, lower_resolved_sakla_command
from .server_data import DataEngine


RuntimeValueResolver = Callable[[str], Any]


def execute_resolved_sakla_command(
    command: Command,
    *,
    binding: ResolvedDataBinding,
    resolve_value: RuntimeValueResolver,
    engine: DataEngine,
    backend_name: str,
) -> DataMutationExecutionResult:
    """Execute canonical ``sakla <Name>`` through the verified mutation chain.

    The command is first bound against authoritative semantic metadata. Only
    after that validation succeeds is the exact resolved value slot read from
    the runtime environment. The resulting value is then written through the
    existing backend/capability validation and transaction-backed execution
    boundary.

    This function intentionally does not infer a model from the runtime value,
    widen the backend/import surface, or bypass the existing ``veri:yaz``
    capability and transaction contract.
    """

    abi = lower_resolved_sakla_command(command, binding=binding)
    value = resolve_value(abi.value_slot)
    return execute_data_mutation(
        abi,
        value=value,
        engine=engine,
        backend_name=backend_name,
    )
