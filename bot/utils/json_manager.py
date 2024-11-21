import json
import os
from typing import Dict, List, Optional


class JsonManager:
    @staticmethod
    def save_to_json(path: str, new_data: dict) -> None:
        data = JsonManager.load_from_json(path)

        if not data:
            data = []

        data.append(new_data)  # type: ignore

        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as error:
            raise Exception(
                f"Unable to save json file: {path} | {error or 'Unknown error'}"
            )

    @staticmethod
    def load_from_json(
        path: str, session_name: Optional[str] = None
    ) -> List[Dict[str, str]] | Dict[str, str]:
        if not os.path.exists(path):
            return []

        try:
            with open(path, "r") as f:
                content = f.read()
                data = json.loads(content)

            if session_name:
                return next(
                    (
                        account
                        for account in data
                        if account["session_name"] == session_name
                    ),
                    {},
                )

            return data
        except json.decoder.JSONDecodeError:
            raise Exception(f"Unable to parse json file: {path}")
        except Exception as error:
            raise Exception(
                f"Unable to load json file: {path} | {error or 'Unknown error'}"
            )
