from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI()

class SteamUser(BaseModel):
    steam_id: int
    name: str
    game_played_app_id: int | None = None
    rich_presence: dict

#post request single person each time
#get request for group of people each time

all_users = {}

@app.post("/people/{steam_id}")
def create_person(steam_id: int, person: SteamUser):
    all_users[steam_id] = person
    return {"message": "Person created", "person": person}


@app.get("/people/")
def return_all_people():
    return {"all_users": list(all_users.values())}

