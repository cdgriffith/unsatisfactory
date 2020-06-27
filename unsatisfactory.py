# -*- coding: utf-8 -*-
#
# MIT License - Copyright (c) 2020 Chris Griffith - See LICENSE
import time
import logging
import datetime
from pathlib import Path
import shutil

import reusables
from appdirs import user_data_dir
from box import Box

logger = logging.getLogger("unsatisfactory")

NUL = b"\x00"

factory_game_folder = Path(user_data_dir(appname="FactoryGame", appauthor=False, roaming=False))
save_game_backup_folder = Path(user_data_dir(appname="Unsatisfactory", appauthor=False, roaming=False))
if not factory_game_folder.exists():
    raise Exception(f"Could not find save game location at {factory_game_folder}")
save_game_folder = factory_game_folder / "Saved" / "SaveGames"

if not save_game_backup_folder.exists():
    save_game_backup_folder.mkdir(exist_ok=True)


def dt():
    return datetime.datetime.now().isoformat().replace(":", "").replace("-", "").rsplit(".")[0]


def perform_backup(manifest):
    corrupt_files = []
    for file in save_game_folder.glob("*/*.sav"):
        if manifest[file.parent.name][file.name].corrupt:
            continue

        contents = file.read_bytes()
        if contents.count(NUL) > (len(contents) / 2) or len(contents) < 100:
            logger.warning(f"{file.parent.name}/{file.name} corrupt!")
            manifest[file.parent.name][file.name].corrupt = True
            corrupt_files.append(file)
            continue

        manifest[file.parent.name][file.name].corrupt = False
        current_hash = reusables.file_hash(file)
        if current_hash == manifest[file.parent.name][file.name].last_hash:
            logger.debug(f"{file.parent.name}/{file.name} has not changed")
            continue
        manifest[file.parent.name][file.name].last_hash = current_hash
        backup_path = save_game_backup_folder / file.parent.name / f"{file.stem}_{dt()}.sav.bak"
        backup_path.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy(file, backup_path)
        if "files" not in manifest[file.parent.name][file.name]:
            manifest[file.parent.name][file.name].files = [str(backup_path)]
        else:
            manifest[file.parent.name][file.name].files.append(str(backup_path))
            if len(manifest[file.parent.name][file.name].files) > 2:
                old_file = manifest[file.parent.name][file.name].files.pop(0)
                Path(old_file).unlink()
        logger.info(f"{file.parent.name}/{file.name} backing up to {backup_path}")
    return corrupt_files


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)-12s  %(levelname)-8s %(message)s")

    manifest_file = save_game_backup_folder / "unsatisfactory.json"
    manifest = (
        Box(default_box=True) if not manifest_file.exists() else Box.from_json(filename=manifest_file, default_box=True)
    )
    while True:
        cf = perform_backup(manifest)
        if cf:
            logger.warning("THERE WERE NEW CORRUPT FILES - {}".format(", ".join([str(x) for x in cf])))
        manifest.to_json(filename=manifest_file, indent=2)
        time.sleep(320)
