from abc import abstractproperty
import os
import random
import string
from pathlib import Path
import logging


class FileMixin:
    def get_directory_name(self) -> str:
        """Make an arbitrary folder in the same folder as the original file to store
        all the images if it doesn't already exist
        """
        if self.directory == None:
            directory = os.path.dirname(self.filename)
            random_directory_name = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=10)
            )
            new_directory = f"{directory}/{random_directory_name}"
            logging.info(f"Generating new directory {new_directory}")
            self.directory = new_directory
            Path(new_directory).mkdir(parents=True, exist_ok=True)
        return self.directory
