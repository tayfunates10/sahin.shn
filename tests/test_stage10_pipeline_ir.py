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
