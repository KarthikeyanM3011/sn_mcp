from pydantic import BaseModel


class ServerConfig(BaseModel):
    debug: bool = False
    timeout: int = 30
    docs_base_url: str = "https://help.moveworks.com/docs"
