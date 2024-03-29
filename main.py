import logging
import uuid
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Cookie, Depends, Request
from passlib.context import CryptContext
from fastapi import FastAPI, HTTPException, Form, Request, Response, WebSocket, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Boolean, Date, Time, select, update
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from captcha.image import ImageCaptcha
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import random
import string
import base64
from io import BytesIO
from datetime import datetime, timedelta
from sqlalchemy.sql import and_
#import pywhatkit
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(filename='error.log', level=logging.ERROR)
logger = logging.getLogger(__name__)

# Función para generar el texto del captcha
def captcha_generator(size: int):
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(size))

# Función para generar el captcha
def generate_captcha():
    captcha: str = captcha_generator(5)
    image = ImageCaptcha()
    data = image.generate(captcha)
    data = base64.b64encode(data.getvalue())
    return {"data": data, "captcha": captcha}

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="740212")

@app.get('/start-session')
def start_session(request: Request):
    captcha = generate_captcha()
    request.session["captcha"] = captcha['captcha']
    captcha_image = captcha["data"]
    return Response(content=base64.b64decode(captcha_image), media_type="image/png")

@app.post('/contact-submission')
def submission(
    request: Request,
    response: Response,
    data: str = Form(...)
):
    if request.session.get("captcha", uuid.uuid4()) == data:
        return status.HTTP_200_OK
    else:
        request.session["captcha"] = str(uuid.uuid4())
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Captcha no coincide")
    
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

engine = create_engine('sqlite:///clientes.db', echo=True)
metadata = MetaData()

clientes = Table(
    'clientes', metadata,
    Column('id', Integer, primary_key=True),
    Column('NombreCompleto', String),
    Column('Telefono', String),
    Column('ObjetivoFitness', String),
    Column('Fecha', Date),
    Column('Hora', Time),
    Column('InformacionSalud', String),
    Column('PreferenciasDieteticas', String),
    Column('CorreoElectronico', String)
)
Reservaciones = Table(
    'Reservaciones', metadata,
    Column('id', Integer, primary_key=True),
    Column('NombreCompleto', String),
    Column('Telefono', String),
    Column('ObjetivoFitness', String),
    Column('Fecha', Date),
    Column('Hora', Time),
    Column('Reservado', Boolean, default=True),
    Column('InformacionSalud', String),
    Column('PreferenciasDieteticas', String),
    Column('CorreoElectronico', String)
)
coach = Table(
    'coach', metadata,
    Column('id', Integer, primary_key=True),
    Column('NombreCompleto', String),
    Column('Telefono', String),
    Column('CorreoElectronico', String),
    Column('hashed_password', String)  # Nueva columna para la contraseña cifrada
)
security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def set_auth_cookie(response: Response, username: str):
    """
    Función para establecer la cookie de autenticación en el objeto response.

    Args:
        response: Objeto Response donde se establece la cookie.
        username: Nombre de usuario que se utilizará como valor de la cookie.
    """
    # Establece la cookie con el nombre de usuario como valor
    response.set_cookie(key="username", value=username, httponly=True, samesite="Strict")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    db = Session(bind=engine)
    coach_record = db.execute(select(coach).where(coach.c.CorreoElectronico == credentials.username)).first()
    if not coach_record:
        raise HTTPException(status_code=400, detail="Usuario o Contraseña Inválidos")
    if not verify_password(credentials.password, coach_record.hashed_password):
        raise HTTPException(status_code=400, detail="Contraseña Inválida")
    return coach_record

print(get_password_hash("contraseña_prueba"))
hashed_password = get_password_hash("contraseña_prueba")
print(verify_password("contraseña_prueba", hashed_password))

metadata.create_all(engine)

@app.on_event("startup")
async def startup_event():
    db = Session(bind=engine)
    try:
        # Comprobar si los coaches ya existen en la base de datos
        coach1 = db.execute(select(coach).where(coach.c.CorreoElectronico == 'teamclayton26@gmail.com')).first()

        # Si no existen, añadirlos a la base de datos
        if not coach1:
            coach1 = coach.insert().values(NombreCompleto='Valeria Clayton', Telefono='+526441456020', CorreoElectronico='teamclayton26@gmail.com', hashed_password=get_password_hash('260802'))
            db.execute(coach1)

        db.commit()
    except Exception as e:
        logger.error(f"Error al añadir coaches a la base de datos: {e}")
        raise HTTPException(status_code=500, detail="Error al añadir coaches a la base de datos")
    finally:
        coaches = db.execute(select(coach)).all()
        for c in coaches:
            print(c.CorreoElectronico, verify_password("260802", c.hashed_password))
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
@app.post("/reservacion_disponible")
async def reservacion_disponible_post(Fecha: str = Form(...), Hora: str = Form(...)):
    try:
        fecha_formateada = datetime.strptime(Fecha, "%Y-%m-%d").date()
        hora_formateada = datetime.strptime(Hora, "%H:%M").time()
        db = Session(bind=engine)
        Reservacion = db.execute(select(Reservaciones).where(and_(Reservaciones.c.Fecha == fecha_formateada, Reservaciones.c.Hora == hora_formateada))).first()

        if Reservacion is None:
            nueva_reservacion = Reservaciones.insert().values(Fecha=fecha_formateada, Hora=hora_formateada, Reservado=True)
            db.execute(nueva_reservacion)
            db.commit()
            return JSONResponse(content={"Reservado": True})
        elif Reservacion and Reservaciones.Reservado:
            db.execute(update(Reservaciones).where(and_(Reservaciones.c.Fecha == fecha_formateada, Reservaciones.c.Hora == hora_formateada)).values(Reservado=False))
            db.commit()
            return JSONResponse(content={"Reservado": True})
        else:
            return JSONResponse(content={"Reservado": False}, status_code=200)
            
    except Exception as e:
        logger.error(f"Error al verificar la disponibilidad de la Reservacion: {e}")
        raise HTTPException(status_code=500, detail="Error al verificar la disponibilidad de la Reservacion")
    finally:
        db.close()

@app.post("/procesar_formulario", response_class=HTMLResponse)
async def procesar_formulario(
    request: Request,
    NombreCompleto: str = Form(...),
    Telefono: str = Form(...),
    ObjetivoFitness: str = Form(...),
    Fecha: str = Form(...),
    Hora: str = Form(...),
    InformacionSalud: str = Form(...),
    PreferenciasDieteticas: str = Form(...),
    CorreoElectronico: str = Form(...)
):
    # Verificar si el número de teléfono es válido
    if not Telefono or Telefono == '+52':
        raise HTTPException(status_code=400, detail="Por favor, ingresa un número de teléfono válido.")
    db = Session(bind=engine)

    # Convertir la cadena de texto de la fecha y la hora a un objeto datetime
    Fecha = datetime.strptime(Fecha, "%Y-%m-%d").date()
    Hora = datetime.strptime(Hora, "%H:%M").time()
    
    print(f"Fecha recibida: {Fecha}")  # Imprime la fecha recibida
    print(f"Hora recibida: {Hora}")  # Imprime la hora recibida
    
    try:
        # Verificar nuevamente si la reservación está disponible antes de procesar el formulario
        
        Reservacion = db.execute(select(Reservaciones).where(and_(Reservaciones.c.Fecha == Fecha, Reservaciones.c.Hora == Hora))).first()
        if Reservacion is not None and not Reservacion.Reservado:
            raise HTTPException(status_code=422, detail="Lo siento, este lugar ya está reservado.")
        
        # Insertamos una nueva reservación en la tabla Reservaciones
        nueva_reservacion = Reservaciones.insert().values(NombreCompleto=NombreCompleto, Telefono=Telefono, ObjetivoFitness=ObjetivoFitness, Fecha=Fecha, Hora=Hora, Reservado=False, InformacionSalud=InformacionSalud, PreferenciasDieteticas=PreferenciasDieteticas, CorreoElectronico=CorreoElectronico)
        db.execute(nueva_reservacion)

        # Resto del código para procesar el formulario
        nuevo_cliente = clientes.insert().values(
            NombreCompleto=NombreCompleto,
            Telefono=Telefono,
            ObjetivoFitness=ObjetivoFitness,
            Fecha=Fecha,
            Hora=Hora,
            InformacionSalud=InformacionSalud,
            PreferenciasDieteticas=PreferenciasDieteticas,
            CorreoElectronico=CorreoElectronico,
        )
        db.execute(nuevo_cliente)
        db.commit()

        # Extraer la hora y los minutos
        # Hora = Hora.hour
        # Enviar un mensaje de WhatsApp
        #pywhatkit.sendwhatmsg_instantly(Telefono, "¡Cita reservada exitosamente!", Hora)
                  
        # Tus credenciales de correo electrónico
        email = "teamclayton26@gmail.com"
        password = "beywfxlirstlutha"

        # Dirección de correo electrónico para enviar el mensaje de texto
        sms_gateway = f"{Telefono}@itelcel.com"

        # Configuración del servidor SMTP
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        # Iniciar el servidor SMTP
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Habilitar cifrado TLS

        # Iniciar sesión en la cuenta de correo electrónico
        server.login(email, password)

        # Crear el mensaje para el SMS
        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = sms_gateway
        msg['Subject'] = "Confirmación de Reservación"  # Asunto del mensaje
        body = "¡Reservación programada exitosamente!"  # Contenido del mensaje
        msg.attach(MIMEText(body, 'plain'))  # Adjuntar el cuerpo del mensaje
        sms = msg.as_string()  # Convertir el mensaje a una cadena

        # Enviar el mensaje de texto (SMS) a través de correo electrónico
        server.sendmail(email, sms_gateway, sms)

        # Crear el mensaje para el correo electrónico
        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = CorreoElectronico
        msg['Subject'] = "Confirmación de Reservación"  # Asunto del mensaje
        body = "¡Reservación programada exitosamente!"  # Contenido del mensaje
        msg.attach(MIMEText(body, 'plain'))  # Adjuntar el cuerpo del mensaje
        email_msg = msg.as_string()  # Convertir el mensaje a una cadena

        # Enviar el correo electrónico
        server.sendmail(email, CorreoElectronico, email_msg)

        # Cerrar la conexión SMTP
        server.quit()

    except HTTPException:
        raise  # Si la excepción ya es HTTPException, la relanzamos
    except Exception as e:
        print(f"Error al procesar formulario: {e}")
        raise HTTPException(status_code=500, detail="Error al procesar formulario")
    finally:
        db.close()
    return templates.TemplateResponse("confirmacion.html", {"request": request, "message": "¡Datos procesados exitosamente!"})

@app.get("/reservaciones_del_dia/{Fecha}")
async def reservaciones_del_dia(Fecha: str):
    db = Session(bind=engine)
    """ Obtiene las reservas del día. Args: Fecha (str): Fecha en formato YYYY-MM-DD. Returns: JSONResponse: Lista de diccionarios con información de las reservas. """
    try:
        fecha_formateada = datetime.strptime(Fecha, "%Y-%m-%d").date()

        # Usa alias 'reservaciones' para simplificar la referencia
        reservaciones_del_dia = db.execute(select(Reservaciones).where(Reservaciones.c.Fecha >= fecha_formateada)).all()

        reservaciones_json = [{
                "id": Reservacion.id,
                "NombreCompleto": Reservacion.NombreCompleto,
                "Telefono": Reservacion.Telefono,
                "ObjetivoFitness": Reservacion.ObjetivoFitness,
                "Reservado": Reservacion.Reservado,
                "Fecha": Reservacion.Fecha.isoformat() if Reservacion.Fecha else None,
                "Hora": Reservacion.Hora.isoformat() if Reservacion.Hora else None,
                "InformacionSalud": Reservacion.InformacionSalud,
                "PreferenciasDieteticas": Reservacion.PreferenciasDieteticas,
                "CorreoElectronico": Reservacion.CorreoElectronico,
            }
            for Reservacion in reservaciones_del_dia ]

        return JSONResponse(content=reservaciones_json)

    except ValueError as e:
        logger.error(f"Error al convertir la fecha: {e}")
        raise HTTPException(status_code=400, detail="Formato de fecha no válido")

    except Exception as e:
        logger.error(f"Error al obtener las reservas del día: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener las reservas del día")

    finally:
        db.close()

@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login(response: Response, request: Request, CorreoElectronico: str = Form(...), plain_password: str = Form(...)):  # Add request argument
    db = Session(bind=engine)
    coach_record = db.execute(select(coach).where(coach.c.CorreoElectronico == CorreoElectronico)).first()
    if not coach_record or not verify_password(plain_password, coach_record.hashed_password):
        raise HTTPException(status_code=400, detail="Usuario o Contraseña Inválidos")

    response.set_cookie(key="username", value=CorreoElectronico, httponly=True, samesite="Strict")
    print("Cookie establecida")

    return templates.TemplateResponse("coaches.html", {"request": request})  # Renderizar la página de entrenadores directamente

@app.get("/coaches", response_class=HTMLResponse)
async def coaches(request: Request, username: str = Cookie(None)):  # Obtener la cookie
    # No es necesaria la verificación de la cookie aquí
    print(f"Username: {username}")  # Imprimir el valor de la cookie (opcional)
    if not username:
        print("Redirigiendo al inicio de sesión")  # Imprimir un mensaje antes de redirigir
        return RedirectResponse(url="/login")  # Redirigir al inicio de sesión si no hay cookie
    return templates.TemplateResponse("coaches.html", {"request": request})  # Corregir el nombre de la plantilla y el orden de los argumentos

@app.get("/logout")
def logout(response: Response):
    response.delete_cookie(key="username")
    return RedirectResponse(url="/login")

@app.get("/disclaimer", response_class=HTMLResponse)
async def disclaimer(request: Request):
    return templates.TemplateResponse("disclaimer.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")