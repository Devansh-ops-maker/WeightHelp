from datetime import datetime, timedelta, timezone
from typing import Annotated 
from dotenv import load_dotenv
import os
import jwt
from database.database import cnx
from models.tokenModel import Token,TokenData
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, status,FastAPI,Request
from fastapi.responses import HTMLResponse
from fastapi.security import  OAuth2PasswordRequestForm,OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from models.courseModel import Course
from models.userModel import User
from models.componentModel import Component
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

load_dotenv()
templates = Jinja2Templates(directory="templates")
app=FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
password_hash = PasswordHash.recommended()
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
ALGORITHM=os.getenv("ALGORITHM")
SECRET_KEY=os.getenv("SECRET_KEY")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.get("/", response_class=HTMLResponse)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request}
    )


@app.get("/register-page", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html",
        {"request": request}
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"request": request}
    )


@app.get("/student/course/{course_code}", response_class=HTMLResponse)
async def course_detail_page(request: Request, course_code: int):
    return templates.TemplateResponse(
        request,
        "course_detail.html",
        {
            "request": request,
            "course_code": course_code
        }
    )

@app.post("/register")
async def registerUser(data:User | None=None)->dict:
    if data is None:
        raise HTTPException(
            status_code=422,
            detail="Invalid field Value"
        )
    else:
        cursor=cnx.cursor()
        hashed_password=get_password(data.password)
        query="INSERT INTO UserData (username,hashed_password) VALUES (%s,%s)"
        cursor.execute(query,(data.username,hashed_password,))
        cnx.commit()
        return {"message":"success"}

def get_password(password):
    return password_hash.hash(password)
@app.post("/login")
async def login(form_data: Annotated[OAuth2PasswordRequestForm,Depends()],) -> Token:
    user=authenticate_user(form_data.username,form_data.password)
    if not user:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")
    
def authenticate_user(username:str,password:str):
    hashed_password=get_user(username)
    if hashed_password is None:
        return False
    if not verify_password(password,hashed_password):
        return False
    return username

def get_user(username:str):
    cursor=cnx.cursor()
    query="SELECT hashed_password from UserData where username=%s"
    cursor.execute(query,(username,))
    hashed_password=cursor.fetchone()
    cursor.close()
    if hashed_password is None:
        return None
    else:
        return hashed_password[0]
def verify_password(plain_password,hashed_password):
    return password_hash.verify(plain_password,hashed_password)
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user=get_user(username=username)
    if user is None:
        raise credentials_exception
    return username
@app.get("/courses",response_model=list[Course])
async def courses(current_user: Annotated[str, Depends(get_current_user)],):
    cursor=cnx.cursor(dictionary=True)
    query="SELECT course_code,course_name FROM Courses WHERE username=%s"
    cursor.execute(query,(current_user,))

    courses=cursor.fetchall()
    cursor.close()

    return courses
@app.post("/addcourse")
async def AddCourses(course: Course,current_user: Annotated[str,Depends(get_current_user)],):
    cursor=cnx.cursor()
    query="INSERT INTO Courses (username,course_code,course_name) VALUES (%s,%s,%s)"
    cursor.execute(query,(current_user,course.course_code,course.course_name))
    cnx.commit()
    cursor.close()
    return {"message":"Course Added Successfully"}
@app.get("/course/{course_code}")
async def getComponents(current_user:Annotated[str,Depends(get_current_user)],course_code: int):
    cursor=cnx.cursor(dictionary=True)
    query="SELECT component_type,weightage,total_marks,obtained_marks FROM Components Where username=%s AND course_code=%s"
    cursor.execute(query,(current_user,course_code))

    components=cursor.fetchall()
    cursor.close()
    resp=[Component(**component) for component in components]
    return resp

@app.post("/course/{course_code}/addComponent")
async def addComponent(current_user:Annotated[str,Depends(get_current_user)],component:Component,course_code:int):
    cursor=cnx.cursor()

    cursor.execute(
    "SELECT 1 FROM Courses WHERE username=%s AND course_code=%s",
    (current_user, course_code)
)

    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    query="INSERT INTO Components (username,course_code,component_type,Weightage,Total_marks,Obtained_marks) VALUES(%s,%s,%s,%s,%s,%s)"
    cursor.execute(query,(current_user,course_code,component.component_type,component.Weightage,component.Total_marks,component.Obtained_marks))
    cnx.commit()
    cursor.close()
    return {"message":"Component Added Successfully"}
    
@app.get("/course/{course_code}/getPercentage")
async def getScore(current_user:Annotated[str,Depends(get_current_user)],course_code:int):
    cursor=cnx.cursor(dictionary=True)
    cursor.execute(
    "SELECT 1 FROM Courses WHERE username=%s AND course_code=%s",
    (current_user, course_code)
)

    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )
    query="SELECT component_type,weightage,total_marks,obtained_marks FROM Components Where username=%s AND course_code=%s"
    cursor.execute(query,(current_user,course_code))

    components=cursor.fetchall()
    cursor.close()
    resp=[Component(**component) for component in components]
    percentage=0.0
    for component in resp:
        curr=component.Obtained_marks/component.Total_marks
        curr=(curr*component.Weightage)
        percentage+=curr
@app.get("/course/{course_code}/getPerfentage")
async def getScore(current_user:Annotated[str,Depends(get_current_user)],course_code:int):
    cursor=cnx.cursor(dictionary=True)
    cursor.execute(
    "SELECT 1 FROM Courses WHERE username=%s AND course_code=%s",
    (current_user, course_code)
)

    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )
    query="SELECT component_type,weightage,total_marks,obtained_marks FROM Components Where username=%s AND course_code=%s"
    cursor.execute(query,(current_user,course_code))

    components=cursor.fetchall()
    cursor.close()
    resp=[Component(**component) for component in components]
    percentage=0.0
    for component in resp:
        curr=component.Obtained_marks/component.Total_marks
        curr=(curr*component.Weightage)
        percentage+=curr
    return {
    "course_code": course_code,
    "percentage": round(percentage, 2)
}





    


