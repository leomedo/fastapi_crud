import re
import uuid

import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional

# Initialize Firebase Admin SDK
cred = credentials.Certificate('fast-api-7db1f-firebase-adminsdk-fbsvc-a6c3cd01d5.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# Create FastAPI instance
app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


class Person(BaseModel):
    name: str
    age: int


@app.post("/create_person/")
async def create_person(person: Person):
    doc_ref = db.collection('person').add(person.dict())
    print(doc_ref[1].id)
    return {**person.dict(), 'id': doc_ref[1].id}


@app.get("/get_person/{person_id}", response_model=Person)
async def get_person(person_id: str):
    doc = db.collection('person').document(person_id).get()
    if doc.exists:
        return Person(**doc.to_dict())
    else:
        raise HTTPException(status_code=404, detail="Person Not Found")


# @app.get("/get_all_person/", response_model=List[Person])
# async def get_all_person():
#     person_ref = db.collection('person')
#     docs = person_ref.stream()
#     d_person = [Person(**doc.to_dict()) for doc in docs]
#     return d_person


@app.get("/get_all_person/", response_model=List[Person])
async def get_all_person(limit: int = Query(10, gt=0), last_doc_id: Optional[str] = None):
    person_ref = db.collection('person').order_by("name")  # استخدم ترتيب معين ثابت

    # لو في آخر مستند، نجيبه و نكمل من بعده
    if last_doc_id:
        last_doc = db.collection('person').document(last_doc_id).get()
        if last_doc.exists:
            person_ref = person_ref.start_after(last_doc)
        else:
            raise HTTPException(status_code=404, detail="Invalid last_doc_id")

    # حدد عدد العناصر
    docs = person_ref.limit(limit).stream()

    result = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id  # أضف id علشان تستخدمه في next request
        result.append(Person(**data))

    return result


@app.put("/person/{person_id}")
async def update_person(person_id: str, person: Person):
    doc_ref = db.collection('person').document(person_id)
    doc_ref.update(person.dict())
    return {**person.dict(), 'id': person_id}


@app.delete("/person/{person_id}")
async def delete_person(person_id: str):
    doc_ref = db.collection('person').document(person_id)
    doc_ref.delete()
    return {"message": "User deleted"}

#################################################################################################


class Task(BaseModel):
    id: str | None = None
    task: str
    description: str | None = None
    duration_minutes: int | None = None


class Topic(BaseModel):
    id: str | None = None
    title: str
    description: str | None = None
    duration_days: int | None = None
    resources: list[str] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)


class Roadmap(BaseModel):
    id: str | None = None
    title: str
    description: str | None = None
    total_duration_weeks: int | None = None
    topics: list[Topic] = Field(default_factory=list)


@app.post("/roadmap", response_model=dict)
async def create_roadmap_endpoint(roadmap: Roadmap):
    topics_data = roadmap.topics
    roadmap_data = roadmap.dict(exclude={"topics"})

    roadmap_id = str(uuid.uuid4())
    roadmap_data["id"] = roadmap_id
    db.collection('roadmaps').document(roadmap_id).set(roadmap_data)

    batch = db.batch()

    for topic in topics_data:
        topic_id = str(uuid.uuid4())
        topic_data = topic.dict(exclude={"tasks"})
        topic_data["id"] = topic_id

        topic_ref = db.collection('roadmaps').document(roadmap_id).collection('topics').document(topic_id)
        batch.set(topic_ref, topic_data)

        for task in topic.tasks:
            task_id = str(uuid.uuid4())
            task_data = task.dict()
            task_data["id"] = task_id

            task_ref = topic_ref.collection('tasks').document(task_id)
            batch.set(task_ref, task_data)

    batch.commit()

    return {
        **roadmap_data,
        "id": roadmap_id
    }


@app.get("/roadmaps", response_model=List[Roadmap])
async def get_all_roadmaps():
    roadmaps_ref = db.collection('roadmaps')
    roadmaps_docs = roadmaps_ref.stream()

    result = []

    for roadmap_doc in roadmaps_docs:
        roadmap_data = roadmap_doc.to_dict()
        roadmap_id = roadmap_doc.id

        topics_ref = db.collection('roadmaps').document(roadmap_id).collection('topics')
        topics_docs = topics_ref.stream()
        topics = []

        for topic_doc in topics_docs:
            topic_data = topic_doc.to_dict()
            topic_id = topic_doc.id

            tasks_ref = topics_ref.document(topic_id).collection('tasks')
            tasks_docs = tasks_ref.stream()
            tasks = [Task(**task_doc.to_dict()) for task_doc in tasks_docs]

            topic_data["tasks"] = tasks
            topics.append(Topic(**topic_data))

        roadmap_data["topics"] = topics
        result.append(Roadmap(**roadmap_data))

    return result


@app.get("/roadmap/{roadmap_id}", response_model=Roadmap)
async def get_roadmap_by_id(roadmap_id: str):
    roadmap_doc = db.collection('roadmaps').document(roadmap_id).get()

    if not roadmap_doc.exists:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    roadmap_data = roadmap_doc.to_dict()
    roadmap_data["id"] = roadmap_doc.id

    # Get topics
    topics_ref = db.collection('roadmaps').document(roadmap_id).collection('topics')
    topics_docs = topics_ref.stream()
    topics = []

    for topic_doc in topics_docs:
        topic_data = topic_doc.to_dict()
        topic_data["id"] = topic_doc.id

        # Get tasks
        tasks_ref = topics_ref.document(topic_doc.id).collection('tasks')
        tasks_docs = tasks_ref.stream()
        tasks = [Task(**{**task_doc.to_dict(), "id": task_doc.id}) for task_doc in tasks_docs]

        topic_data["tasks"] = tasks
        topics.append(Topic(**topic_data))

    roadmap_data["topics"] = topics
    return Roadmap(**roadmap_data)
