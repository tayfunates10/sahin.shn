from sahin.ir import IRInstruction, lower_source


def test_pipeline_lowers_stages_in_source_order() -> None:
    program = lower_source("sonuç = 1..5\n    | ilk 2\n    | seç evet\n")

    pipeline = [item for item in program.instructions if item.opcode == "pipeline"]
    assert len(pipeline) == 2
    assert pipeline[0].operands[0] == "ilk"
    assert pipeline[1].operands[0] == "seç"
    assert pipeline[1].operands[1] == pipeline[0].result


def test_pipeline_arguments_are_evaluated_before_stage_instruction() -> None:
    program = lower_source("sonuç = 1..5\n    | ilk 2\n")
    instructions = list(program.instructions)
    pipeline_index = next(i for i, item in enumerate(instructions) if item.opcode == "pipeline")
    stage = instructions[pipeline_index]

    assert stage.operands[0] == "ilk"
    assert stage.operands[1].startswith("%")
    assert stage.operands[2].startswith("%")
    assert any(item.result == stage.operands[2] for item in instructions[:pipeline_index])


def test_pipeline_opcode_has_explicit_result() -> None:
    program = lower_source("sonuç = 3..1\n    | sırala\n")
    stage = next(item for item in program.instructions if item.opcode == "pipeline")
    assert isinstance(stage, IRInstruction)
    assert stage.result is not None


def test_pipeline_implicit_field_selector_lowers_as_text_literal() -> None:
    program = lower_source("sonuç = 1..5\n    | sırala ad\n    | seç aktif\n")
    instructions = list(program.instructions)
    stages = [item for item in instructions if item.opcode == "pipeline"]

    assert len(stages) == 2
    selector_literals = {
        item.result: item.operands[0]
        for item in instructions
        if item.opcode == "const" and item.result is not None
    }
    assert selector_literals[stages[0].operands[2]] == 'metin:"ad"'
    assert selector_literals[stages[1].operands[2]] == 'metin:"aktif"'


def test_pipeline_extra_arguments_are_not_evaluated_like_reference_runtime() -> None:
    program = lower_source("sonuç = 1..5\n    | ilk 1, (1 / 0)\n")
    stage = next(item for item in program.instructions if item.opcode == "pipeline")

    assert len(stage.operands) == 3
    assert not any(
        item.opcode == "binary" and item.operands and item.operands[0] == "/"
        for item in program.instructions
    )
