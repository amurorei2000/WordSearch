import os
from fastapi import FastAPI, HTTPException, Depends, WebSocket
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from database import SessionLocal, User, Answers
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError

app = FastAPI()
# db= engine.connect()

# 회원가입 데이터 폼
class UserCreate(BaseModel):
    user_id: str
    password: str

# 로그인 데이터 폼
class UserLogin(BaseModel):
    user_id: str
    password: str
    
# JWT 액세스 토큰 폼
class JWT_Token(BaseModel):
    status: str
    message: str
    access_token: str
    token_type: str
    
# 정답 데이터 폼
class CheckAnswer(BaseModel):
    category: str
    answer: str

SECRET_KEY = "super-coding"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 스키마
oauth2_schema = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/")
async def root():
    return {"message": "Hello World!"}

# 전체 유저 조회
@app.get("/users")
async def get_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        res = {}
        for user in users:
            print(f"id: {user.user_id}\tpassword: {user.password}")
            res.update({"id": user.user_id, "pwd": user.password})
        # result = db.execute(text("SELECT * FROM users"))
        # for row in result:
        #     res.update({"id": row[1], "pwd": row[2]})
            
        return res
    except HTTPException as e:
        print(f"에러: {str(e)}")
    finally:
        db.close()
    

# 회원 가입
@app.post("/signup")
async def signup(user: UserCreate):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.user_id == user.user_id).first():
            raise HTTPException(status_code=400, detail="이미 존재하는 ID 입니다.")
        
        new_user = User(
            user_id=user.user_id,
            password=user.password
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {"status": "success", "message": "회원 가입에 성공했습니다."}
    except Exception as e:
        print(f"에러: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="회원 가입 실패")
    finally:
        db.close()


# JWT 토큰 생성
def create_access_token(data, expire_delta):
    to_encode = data.copy()
    
    secret = os.environ.get("SECRET_KEY")
    algo = os.environ.get("ALGORITHM")
    exp = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # 유효기간 값이 있을 때
    if expire_delta:
        expire = datetime.now(timezone.utc) + expire_delta
    # 유효기간 값이 없으면 30분
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(claims=to_encode,
                                key=SECRET_KEY,
                                algorithm=ALGORITHM)
    return encoded_jwt


# 로그인
@app.post("/login", response_model=JWT_Token)
async def login(user: UserLogin):
    db = SessionLocal()
    try:
        find_user = db.query(User).filter(User.user_id == user.user_id).first()
        pwd = getattr(find_user, "password")
        
        # 유저 정보를 db 데이터와 대조하기
        if not find_user:
            raise HTTPException(status_code=401,
                                detail="없는 사용자입니다.",
                                headers={"WWW-Authenticate": "Bearer"})
        elif pwd != user.password:
            raise HTTPException(status_code=401,
                                detail="패스워드 오류입니다.",
                                headers={"WWW-Authenticate": "Bearer"})
        
        # 토큰 유효기간 설정
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # 토큰 생성
        access_token = create_access_token(data={"sub": find_user.user_id},
                                           expire_delta=access_token_expires)
        
        # 토큰 값을 클라이언트에게 반환
        return {
                "status": "success",
                "message": "로그인에 성공했습니다!",
                "access_token": access_token,
                "token_type": "bearer"
                }
            
    except Exception as e:
        print(f"에러: {str(e)}")
        raise HTTPException(status_code=500, detail="로그인 실패")
    finally:
        db.close()
        
# JWT 토큰으로 현재 유저 가져오기
async def get_current_user(token: str = Depends(oauth2_schema)):
    db = SessionLocal()

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    # 토큰에 있는 유저 아이디 정보 확인
    try:
        payload = jwt.decode(token=token, key=SECRET_KEY, algorithms=ALGORITHM)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    # db에 있는 유저인지 확인
    try:
        find_user = db.query(User).filter(User.user_id == user_id).first()
        if find_user is None:
            raise credentials_exception
        return find_user
    except Exception as e:
        print(f"에러: {str(e)}")
    finally:
        db.close()


@app.post("/checkCorrectAnswer")
async def checkCorrectAnswer(answer: CheckAnswer, current_user = Depends(get_current_user)):
    db = SessionLocal()
    # print(answer.category, answer.answer)
    try:
        res = db.query(Answers).filter(Answers.category == answer.category).all()
        db_answers = [r.answer for r in res]
        # db_answers = db.execute(text(f"SELECT answer FROM answers WHERE category='{answer.category}'"))
        print("정답 리스트: ", db_answers)
        for ans in db_answers:
            if answer.answer == ans:
                result = True
                print("정답: ", ans)
                break
            else:
                result = False
        
        return {"status": "success", "message": result}
    except Exception as e:
        print(f"에러: {str(e)}")
    finally:
        db.close()

@app.websocket("/ws")
async def current_state(websocket: WebSocket):
    print(f"클라이언트 연결: {websocket.client}")
    await websocket.accept()
    # await websocket.send_text(f"연결된 클라이언트: {websocket.client}")
    
    correct_list = []
    
    while True:
        # 수신 대기
        data = await websocket.receive_text()
        print(f"정답 목록 작성 요청: {data} - {websocket.client}")
        
        correct_list.append(data)
        
        await websocket.send_json({"correct" : correct_list})
        