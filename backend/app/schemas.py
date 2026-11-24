from pydantic import BaseModel, EmailStr, Field

class Register(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class Login(BaseModel):
    email: EmailStr
    password: str

class ImportGame(BaseModel):
    pgn: str = Field(min_length=10, max_length=500_000)

class GameOut(BaseModel):
    id: str
    white_player: str
    black_player: str
    result: str
    event: str
    played_at: str | None
    move_count: int
    class Config: from_attributes = True
