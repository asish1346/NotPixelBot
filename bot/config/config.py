from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    PLAY_INTRO: bool = True
    INITIAL_START_DELAY_SECONDS: list[int] = [10, 240]  # in seconds
    ITERATION_SLEEP_MINUTES: list[int] = [60, 120]  # in minutes
    ENABLE_SSL: bool = True

    USE_REF: bool = True
    REF_ID: str = "f2087936510"  # It would be great if you didn't change it, but I'm not stopping you

    SLEEP_AT_NIGHT: bool = True
    NIGHT_START_HOURS: list[int] = [0, 2]  # 24 hour format in your timezone
    NIGHT_END_HOURS: list[int] = [6, 8]  # 24 hour format in your timezone
    ADDITIONAL_NIGHT_SLEEP_MINUTES: list[int] = [2, 45]  # in minutes
    ROUND_START_TIME_DELTA_MINUTES: int = 30  # in minutes
    ROUND_END_TIME_DELTA_MINUTES: int = 30  # in minutes

    CLAIM_PX: bool = True
    UPGRADE_BOOSTS: bool = True
    PAINT_PIXELS: bool = True
    COMPLETE_TASKS: bool = True
    PARTICIPATE_IN_TOURNAMENT: bool = True
    COMPLETE_QUESTS: bool = True
    COMPLETE_DANGER_TASKS: bool = False
    WATCH_ADS: bool = False
    USE_ALL_CHARGES: bool = True
    RESELECT_TOURNAMENT_TEMPLATE: bool = False
    CHECK_BOT_STATE: bool = True


settings = Settings()  # type: ignore
