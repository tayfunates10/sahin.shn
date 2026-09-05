from sahin.ast_nodes import Command, Name
from sahin.ir import lower_source
from sahin.lexer import tokenize
from sahin.parser import parse
from sahin.runtime import Runtime


def test_direct_name_mutation_parses_as_subject_command():
    program = parse(tokenize("stok = 3\nstok artır 2\n"))

    command = program.statements[1]
    assert isinstance(command, Command)
    assert command.name == "artır"
    assert isinstance(command.subject, Name)
    assert command.subject.value == "stok"
    assert len(command.arguments) == 1


def test_direct_name_mutation_matches_reference_runtime():
    program = parse(tokenize("stok = 3\nstok artır 2\nstok azalt 1\n"))

    values = Runtime(output=lambda _: None).execute(program)
    assert values["stok"] == 4


def test_direct_name_mutation_lowers_to_existing_ir_primitives():
    ir = lower_source("stok = 3\nstok artır 2\n")

    assert [item.opcode for item in ir.instructions] == [
        "const",
        "store",
        "load",
        "const",
        "binary",
        "store",
    ]
    assert ir.instructions[4].operands[0] == "+"
