from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # CORS: фронтенд на Next.js. В проде сюда кладётся домен.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Игровые дефолты/границы.
    round_seconds_default: int = 80
    round_seconds_min: int = 20
    round_seconds_max: int = 180
    total_turns_default: int = 6
    total_turns_min: int = 1
    total_turns_max: int = 30
    min_players_to_start: int = 2

    # Паузы между фазами (сек).
    turn_end_pause: float = 6.0
    game_end_pause: float = 15.0

    # Очки.
    guesser_base: int = 100  # макс. очки за мгновенную догадку
    guesser_min: int = 20  # минимум за догадку у самого конца таймера
    drawer_base: int = 60  # бонус рисующему при 100% угадавших

    # Логирование.
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
