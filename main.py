import logging
from fastapi import FastAPI, HTTPException, Form, Request, WebSocket, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Boolean, DateTime, select, update
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
from sqlalchemy.sql import and_
from datetime import time as Time
from sqlalchemy import Date
from sqlalchemy import Time
# Agregar estas líneas para desactivar el modo FAILSAFE de pyautogui
# import pyautogui
# pyautogui.FAILSAFE = False
# pyautogui._pyautogui_x11._display = None
# import pywhatkit
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

engine = create_engine('sqlite:///pacientes.db', echo=True)
metadata = MetaData()

pacientes = Table(
    'pacientes', metadata,
    Column('id', Integer, primary_key=True),
    Column('nombre_completo', String),
    Column('edad', Integer),
    Column('telefono', String),
    Column('fecha_hora_cita', DateTime),
    Column('motivo_cita', String),
    Column('notas_cita', String),
    Column('correo_electronico', String)
)
citas = Table(
    'citas', metadata,
    Column('id', Integer, primary_key=True),
    Column('fecha', Date),
    Column('hora', Time),
    Column('disponible', Boolean, default=True)
)
medicos = Table(
    'medicos', metadata,
    Column('id', Integer, primary_key=True),
    Column('nombre', String),
    Column('telefono', String),
    Column('correo_electronico', String)
)
metadata.create_all(engine)

@app.lifespan.on_startup
async def startup_event():
    db = Session(bind=engine)
    try:
        # Añadir médicos a la base de datos
        medico1 = medicos.insert().values(nombre='Pedro Perez', telefono='+525581073859', correo_electronico='generalmanager@maritimeprotection.mx')
        medico2 = medicos.insert().values(nombre='Julian Lugo', telefono='+526444475422', correo_electronico='jlugog1274@gmail.com')

        db.execute(medico1)
        db.execute(medico2)
        db.commit()
    except Exception as e:
        logger.error(f"Error al añadir médicos a la base de datos: {e}")
        raise HTTPException(status_code=500, detail="Error al añadir médicos a la base de datos")
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/cita_disponible")
async def cita_disponible_post(fecha: str = Form(...), hora: str = Form(...)):
    try:
        fecha_formateada = datetime.strptime(fecha, "%Y-%m-%d").date()
        hora_formateada = datetime.strptime(hora, "%H:%M").time()
        db = Session(bind=engine)
        cita = db.execute(select(citas).where(and_(citas.c.fecha == fecha_formateada, citas.c.hora == hora_formateada))).first()

        if cita is None:
            nueva_cita = citas.insert().values(fecha=fecha_formateada, hora=hora_formateada, disponible=True)
            db.execute(nueva_cita)
            db.commit()
            return JSONResponse(content={"disponible": True})
        elif cita and cita.disponible:
            db.execute(update(citas).where(and_(citas.c.fecha == fecha_formateada, citas.c.hora == hora_formateada)).values(disponible=False))
            db.commit()
            return JSONResponse(content={"disponible": True})
        else:
            return JSONResponse(content={"disponible": False}, status_code=200)

    except Exception as e:
        logger.error(f"Error al verificar la disponibilidad de la cita: {e}")
        raise HTTPException(status_code=500, detail="Error al verificar la disponibilidad de la cita")
    finally:
        db.close()

@app.post("/procesar_formulario", response_class=HTMLResponse)
async def procesar_formulario(
    request: Request,
    NombreCompleto: str = Form(...),
    Edad: str = Form(...),
    Telefono: str = Form(...),
    FechaCita: str = Form(...),
    HoraCita: str = Form(...),
    MotivoCita: str = Form(...),
    NotasCita: str = Form(...),
    Correo_Electronico: str = Form(...)
):
    db = Session(bind=engine)

    fecha_cita = datetime.strptime(FechaCita, "%Y-%m-%d").date()
    hora_cita = datetime.strptime(HoraCita, "%H:%M").time()

    try:
        # Verificamos nuevamente si la cita está disponible antes de procesar el formulario
        cita = db.execute(select(citas).where(and_(citas.c.fecha == fecha_cita, citas.c.hora == hora_cita))).first()
        if cita is not None and not cita.disponible:
            raise HTTPException(status_code=422, detail="Lo siento, esta cita ya está reservada.")
        
        # Insertamos una nueva cita en la tabla citas
        nueva_cita = citas.insert().values(fecha=fecha_cita, hora=hora_cita, disponible=False)
        db.execute(nueva_cita)
        
        # Resto del código para procesar el formulario
        nuevo_paciente = pacientes.insert().values(
            nombre_completo=NombreCompleto,
            edad=Edad,
            telefono=Telefono,
            fecha_hora_cita=datetime.combine(fecha_cita, hora_cita),
            motivo_cita=MotivoCita,
            notas_cita=NotasCita,
            correo_electronico=Correo_Electronico
        )
        db.execute(nuevo_paciente)
        db.commit()

        # Enviar un mensaje de WhatsApp
        # pywhatkit.sendwhatmsg_instantly(Telefono, "¡Cita reservada exitosamente!", hora_cita.hour, hora_cita.minute)

        # Enviar un correo electrónico
        msg = MIMEMultipart()
        msg['From'] = 'marketingconsultantsmx@gmail.com'
        msg['To'] = Correo_Electronico
        msg['Subject'] = 'Confirmación de cita'
        message = '¡Cita reservada exitosamente!'
        msg.attach(MIMEText(message))

        mailserver = smtplib.SMTP('smtp.gmail.com', 587)
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.ehlo()
        mailserver.login('marketingconsultantsmx@gmail.com', 'dcfcusagrzhhcmyx')
        mailserver.sendmail('marketingconsultantsmx@gmail.com', Correo_Electronico, msg.as_string())
        mailserver.quit()

    except HTTPException:
        raise  # Si la excepción ya es HTTPException, la relanzamos
    except Exception as e:
        logger.error(f"Error al procesar formulario: {e}")
        raise HTTPException(status_code=500, detail="Error al procesar formulario")
    finally:
        db.close()

    return templates.TemplateResponse("confirmacion.html", {"request": request, "message": "¡Datos procesados exitosamente!"})

@app.get("/citas_del_dia/{fecha}")
async def citas_del_dia(fecha: str):
    fecha_formateada = datetime.strptime(fecha, "%Y-%m-%d").date()
    db = Session(bind=engine)
    try:
        # Usa alias 'pac' para simplificar la referencia
        citas_del_dia = db.execute(select(pacientes).where(pacientes.c.fecha_hora_cita >= fecha_formateada)).all()
        citas_json = [{
            'id': cita.id,
            'nombre_completo': cita.nombre_completo,
            'edad': cita.edad,
            'telefono': cita.telefono,
            'fecha_hora_cita': cita.fecha_hora_cita.isoformat() if cita.fecha_hora_cita else None,
            'motivo_cita': cita.motivo_cita,
            'notas_cita': cita.notas_cita,
            'correo_electronico': cita.correo_electronico
        } for cita in citas_del_dia]
        return JSONResponse(content=citas_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/terapeutas", response_class=HTMLResponse)
async def terapeutas(request: Request):
    return templates.TemplateResponse("terapeutas.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")
