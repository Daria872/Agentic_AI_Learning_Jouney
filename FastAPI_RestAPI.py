#API->Allows two software applications to communicate with each other
#Eg: A customer issues a request(food) and it gets communicated to the kitchen(server) through the waiter(api). The response is then sent through the api from kitchen to the customer

#CRUD
#Create->POST: To add smthg new
#Read->GET: To show a piece of information
#Update->PUT/PATCH: To update smthg
#Delete->DELETE: To delete/remove smthg

#Client-> Sends the request to the server
#Sever-> Processes the request and sends the response back to the client
#To check is the response is sucessfull or not, we use status codes

#JSON-> Collection of arrays and objects(key-value pairs)

#FastAPI-> Python framework to build apis
#Convert python objects to JSON and vice versa; validate different results; ensure correct data is provided

#Set up:
# pip install fastapi uvicorn pydantic

#Pydantic-> Data validation library used in python

from fastapi import FastAPI, HTTPException
#import basemodel from pydantic
from pydantic import BaseModel, field_validator
#from typing import optional, list
from typing import List, Optional
#add a unique identifier
from uuid import UUID, uuid4

app=FastAPI()

class Task(BaseModel): #create a class that inherits from BaseModel
    id: Optional[UUID]=None
    title: str
    description: Optional[str]=None
    completed: bool=False

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Title cannot be blank")
        return value

tasks=[] #To store the objects

#Same endpoint is allowed as long as the request type is different

@app.get("/")
def read():
    return {"hello":"world"}

#Read all tasks from the list
@app.get("/tasks", response_model=List[Task])
def read_tasks():
    return tasks

#To post i.e. accept a new task and add it in tasks
@app.post("/tasks", response_model=Task)
def create_task(task: Task): #Accept a new task which is basically of type Task
    #So, all we have to enter is title since other fields are optional
    task.id = uuid4() #Provides us with a new unique identifier
    tasks.append(task)
    return task

@app.get("/tasks/{task_id}", response_model=Task)
def read_task(task_id:UUID): #Read a specific task with a certain uuid
    for task in tasks:
        if task.id==task_id:
            return task

    raise HTTPException(status_code=404, detail="Task Not Found")

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: UUID, updated_task: Task):
    for index, task in enumerate(tasks):
        if task.id == task_id:
            updated_task.id = task_id
            tasks[index] = updated_task
            return updated_task

    raise HTTPException(status_code=404, detail="Task Not Found")

@app.delete("/tasks/{task_id}")
def delete_task(task_id: UUID):
    for index, task in enumerate(tasks):
        if task.id == task_id:
            tasks.pop(index)
            return {"message": "Task deleted"}

    raise HTTPException(status_code=404, detail="Task Not Found")


if __name__=="__main__":
    import uvicorn

    uvicorn.run(app)

#http://127.0.0.1:8000/ -> {"hello":"world"}
#http://127.0.0.1:8000/docs -> {GET}
#POST /tasks with {"title": "Learn FastAPI"} creates a task

#PYDANTIC
#Use an in-memory database, once the server is lot, data is also lost

#Serialize a Pydantic model as a JSON string:
#task = Task(title="Learn Pydantic")
#print(task.model_dump_json())
