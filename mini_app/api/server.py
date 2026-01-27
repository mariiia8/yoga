from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import logging
from database import Session, Class, SubscriptionType, Subscription, User, Booking
from fastapi.responses import JSONResponse
from datetime import datetime

# Настройка логгирования
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Раздача статики (HTML/JS/CSS)
app.mount("/static", StaticFiles(directory="mini_app/pages"), name="static")


@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open(Path("mini_app/pages/main/index.html"), "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)


@app.get("/schedule", response_class=HTMLResponse)
async def read_schedule():
    return FileResponse("mini_app/pages/schedule/index.html")


@app.get("/subscriptions", response_class=HTMLResponse)
async def read_subscriptions():
    return FileResponse("mini_app/pages/subscriptions/index.html")
    

@app.get("/bookings", response_class=HTMLResponse)
async def read_subscriptions():
    return FileResponse("mini_app/pages/bookings/index.html")


@app.get("/api/classes")
async def get_classes(user_id: int):
    try:
        with Session() as session:
            classes = session.query(Class).all()
            return [{
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "datetime": c.datetime.isoformat() if c.datetime else None,
                "price": c.price,
                "max_participants": c.max_participants
            } for c in classes]
    except Exception as e:
        logger.error(f"Error in get_classes: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/book")
async def book_class(request: Request):
    try:
        data = await request.json()
        logger.info(f"Booking request: {data}")
        
        with Session() as session:
            # Проверяем существование пользователя
            user = session.query(User).filter_by(telegram_id=data['user_id']).first()
            if not user:
                return JSONResponse({"error": "User not found"}, status_code=404)
            
            # Проверяем существование занятия
            class_ = session.query(Class).filter_by(id=data['class_id']).first()
            if not class_:
                return JSONResponse({"error": "Class not found"}, status_code=404)
            
            # Проверяем, не записан ли уже пользователь
            existing_booking = session.query(Booking).filter_by(
                user_id=user.id,
                class_id=data['class_id']
            ).first()
            
            if class_.datetime < datetime.now():
                return JSONResponse(
                    {"error": "Class elready finished"},
                    status_code=400
                )
            
            if existing_booking:
                return JSONResponse(
                    {"error": "User already booked this class"},
                    status_code=400
                )
                
            current_bookings = session.query(Booking).filter_by(class_id=data['class_id']).count()
            if current_bookings >= class_.max_participants:
                return JSONResponse(
                    {"error": "No available spots left"},
                    status_code=400
                )
            
            # Создаем новую запись
            new_booking = Booking(
                user_id=user.id,
                class_id=data['class_id']
            )
            session.add(new_booking)
            session.commit()
            
            return {
                "status": "success",
                "booking_id": new_booking.id
            }
            
    except Exception as e:
        logger.error(f"Error in book_class: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )
    
    
@app.get("/api/user/subscriptions")
async def get_user_subscriptions(user_id: int):
    session = Session()
    subscriptions = session.query(Subscription).filter_by(user_id=user_id).all()
    return [{
        "id": s.id,
        "name": s.subscription_type.name,
        "visits_remaining": s.visits_remaining
    } for s in subscriptions]


@app.post("/api/admin/create_class")
async def create_class(request: Request):
    data = await request.json()
    session = Session()
    new_class = Class(
        name=data['name'],
        description=data['description'],
        datetime=data['datetime'],
        max_participants=data['max_participants'],
        price=data['price']
    )
    session.add(new_class)
    session.commit()
    return {"status": "success", "class_id": new_class.id}
    
    
@app.get("/api/user/active_subscriptions")
async def get_active_subscriptions(user_id: int):
    try:
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                return JSONResponse({"error": "User not found"}, status_code=404)
            
            subscriptions = session.query(Subscription).filter(
                Subscription.user_id == user.id,
                Subscription.visits_remaining > 0
            ).join(Subscription.subscription_type).all()
            
            return [{
                "id": sub.id,
                "name": sub.subscription_type.name,
                "class_name": sub.subscription_type.class_.name,
                "class_id": sub.subscription_type.class_.id,
                "visits_allowed": sub.subscription_type.visits_allowed,
                "visits_remaining": sub.visits_remaining,
                "price": sub.subscription_type.price,
                "purchase_date": sub.purchase_date.isoformat() if sub.purchase_date else None
            } for sub in subscriptions]
    except Exception as e:
        logger.error(f"Error in get_active_subscriptions: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/subscriptions/purchase")
async def purchase_subscription(request: Request):
    try:
        data = await request.json()
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=data['user_id']).first()
            if not user:
                return JSONResponse({"error": "User not found"}, status_code=404)
            
            subscription_type = session.query(SubscriptionType).filter_by(
                id=data['subscription_type_id']
            ).first()
            if not subscription_type:
                return JSONResponse({"error": "Subscription type not found"}, status_code=404)
            
            new_subscription = Subscription(
                user_id=user.id,
                subscription_type_id=subscription_type.id,
                visits_remaining=subscription_type.visits_allowed
            )
            session.add(new_subscription)
            session.commit()
            
            return {"status": "success", "subscription_id": new_subscription.id}
    except Exception as e:
        logger.error(f"Error in purchase_subscription: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/class/{class_id}")
async def get_class(class_id: int):
    try:
        with Session() as session:
            class_ = session.query(Class).filter_by(id=class_id).first()
            if not class_:
                return JSONResponse({"error": "Class not found"}, status_code=404)
            
            return {
                "id": class_.id,
                "name": class_.name,
                "description": class_.description,
                "datetime": class_.datetime.isoformat(),
                "price": class_.price,
                "max_participants": class_.max_participants
            }
    except Exception as e:
        logger.error(f"Error in get_class: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
        
        
@app.get("/api/class/{class_id}/subscription_types")
async def get_class_subscription_types(class_id: int):
    try:
        with Session() as session:
            subscription_types = session.query(SubscriptionType).filter_by(
                class_id=class_id
            ).all()
            
            if not subscription_types:
                return JSONResponse(
                    content={"error": "No subscription types found for this class"},
                    status_code=404
                )
            
            return [{
                "id": st.id,
                "name": st.name,
                "visits_allowed": st.visits_allowed,
                "price": st.price
            } for st in subscription_types]
    except Exception as e:
        logger.error(f"Error in get_class_subscription_types: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.get("/api/user/bookings")
async def get_user_bookings(user_id: int):
    try:
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                return JSONResponse({"error": "User not found"}, status_code=404)
            
            bookings = session.query(Booking).filter_by(user_id=user.id).join(Booking.class_).all()
            
            result = []
            for booking in bookings:
                is_past = booking.class_.datetime < datetime.now()
                result.append({
                    "id": booking.id,
                    "class_id": booking.class_id,
                    "class_name": booking.class_.name,
                    "description": booking.class_.description,
                    "class_datetime": booking.class_.datetime.isoformat(),
                    "price": booking.class_.price,
                    "can_cancel": not is_past
                })
            
            return result
            
    except Exception as e:
        logger.error(f"Error in get_user_bookings: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/cancel_booking")
async def cancel_booking(request: Request):
    try:
        data = await request.json()
        print(f"Cancel booking request data: {data}")  # Добавлено логирование

        if 'booking_id' not in data or 'user_id' not in data:
            return JSONResponse(
                {"error": "Missing booking_id or user_id in request"},
                status_code=400
            )

        with Session() as session:
            user = session.query(User).filter_by(telegram_id=data['user_id']).first()
            if not user:
                return JSONResponse({"error": "User not found"}, status_code=404)
            
            booking = session.query(Booking).filter(
                Booking.id == data['booking_id'],
                Booking.user_id == user.id
            ).first()

            if not booking:
                return JSONResponse({"error": "Booking not found"}, status_code=404)
            
            # Проверяем что занятие еще не прошло
            class_ = session.query(Class).filter_by(id=booking.class_id).first()
            if not class_:
                return JSONResponse({"error": "Class not found"}, status_code=404)
                
            if class_.datetime < datetime.now():
                return JSONResponse(
                    {"error": "Cannot cancel past class"}, 
                    status_code=400
                )
            
            session.delete(booking)
            session.commit()
            return {"status": "success"}

    except Exception as e:
        logger.error(f"Error in cancel_booking: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
        
    
    
@app.exception_handler(Exception)
async def universal_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
