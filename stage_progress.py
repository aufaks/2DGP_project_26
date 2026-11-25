from pathlib import Path


WORLD_COUNT = 4
STAGES_PER_WORLD = 9
STAGE_ROOT = Path(__file__).resolve().parent / 'stages'


def stage_path(world_number, stage_number):
    if not (1 <= world_number <= WORLD_COUNT and
            1 <= stage_number <= STAGES_PER_WORLD):
        raise ValueError('Stage is outside the four-world, nine-stage sequence.')
    return STAGE_ROOT / f'world_{world_number:02d}' / f'stage_{stage_number:02d}.json'


def next_stage(world_number, stage_number):
    if stage_number < STAGES_PER_WORLD:
        return world_number, stage_number + 1
    if world_number < WORLD_COUNT:
        return world_number + 1, 1
    return None
