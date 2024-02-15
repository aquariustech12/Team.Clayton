import logging
from fastapi import FastAPI, HTTPException, Form, Request, WebSocket, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Boolean, DateTime, select, update
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
import pywhatkit
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
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
    Column('Disponibilidad', DateTime),
    Column('InformacionSalud', String),
    Column('PreferenciasDieteticas', String),
    Column('CorreoElectronico', String)
)
Reservaciones = Table(
    'Reservaciones', metadata,
    Column('id', Integer, primary_key=True),
    Column('Disponibilidad', DateTime),  # Cambiado de Boolean a DateTime
)
coach = Table(
    'coach', metadata,
    Column('id', Integer, primary_key=True),
    Column('NombreCompleto', String),
    Column('Telefono', String),
    Column('CorreoElectronico', String)
)
metadata.create_all(engine)

@app.on_event("startup")
async def startup_event():
    db = Session(bind=engine)
    try:
        # Añadir coach a la base de datos
        coach1 = coach.insert().values(NombreCompleto='Valeria Clayton', Telefono='+526441456020', CorreoElectronico='teamclayton26@gmail.com')
        coach2 = coach.insert().values(NombreCompleto='Julian Lugo', Telefono='+526444475422', CorreoElectronico='jlugog1274@gmail.com')

        db.execute(coach1)
        db.execute(coach2)
        db.commit()
    except Exception as e:
        logger.error(f"Error al añadir coaches a la base de datos: {e}")
        raise HTTPException(status_code=500, detail="Error al añadir coaches a la base de datos")
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/reservacion_disponible")
async def reservacion_disponible_post(fecha: str = Form(...), hora: str = Form(...)):
    try:
        fecha_formateada = datetime.strptime(fecha, "%Y-%m-%d").date()
        hora_formateada = datetime.strptime(hora, "%H:%M").time()
        db = Session(bind=engine)
        reservacion_disponible = db.execute(select(Reservaciones).where((Reservaciones.c.fecha == fecha_formateada, Reservaciones.c.hora == hora_formateada))).first()

        if reservacion_disponible is None:
            reservacion_nueva = Reservaciones.insert().values(fecha=fecha_formateada, hora=hora_formateada, Disponibilidad=True)
            db.execute(reservacion_nueva)
            db.commit()
            return JSONResponse(content={"disponible": True})
        elif reservacion_disponible and reservacion_disponible.Disponibilidad:
            db.execute(update(Reservaciones).where((Reservaciones.c.fecha == fecha_formateada, Reservaciones.c.hora == hora_formateada)).values(Disponibilidad=False))
            db.commit()
            return JSONResponse(content={"disponible": True})
        else:
            return JSONResponse(content={"disponible": False}, status_code=200)

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
    Disponibilidad: str = Form(...),
    InformacionSalud: str = Form(...),
    CorreoElectronico: str = Form(...)
):
    db = Session(bind=engine)

    # Convertir la cadena de texto de la disponibilidad a un objeto datetime
    disponibilidad_reservacion = datetime.strptime(Disponibilidad, "%H:%M %Y-%m-%d")


    try:
        # Verificar nuevamente si la reservación está disponible antes de procesar el formulario
        reservacion_disponible = db.execute(select(Reservaciones).where(Reservaciones.c.Disponibilidad == disponibilidad_reservacion)).first()
        if reservacion_disponible is not None and not reservacion_disponible.Disponibilidad:
            raise HTTPException(status_code=422, detail="Lo siento, este lugar ya está reservado.")
        
        # Insertar una nueva reservación en la tabla Reservaciones
        nueva_reservacion = Reservaciones.insert().values(Disponibilidad=disponibilidad_reservacion)
        db.execute(nueva_reservacion)

        # Resto del código para procesar el formulario
        nuevo_cliente = clientes.insert().values(
            NombreCompleto=NombreCompleto,
            Telefono=Telefono,
            ObjetivoFitness=ObjetivoFitness,
            Disponibilidad=disponibilidad_reservacion,
            InformacionSalud=InformacionSalud,
            CorreoElectronico=CorreoElectronico,
        )
        db.execute(nuevo_cliente)
        db.commit()


        # Enviar un mensaje de WhatsApp
        pywhatkit.sendwhatmsg_instantly(Telefono, "¡Reservación programada exitosamente!", Disponibilidad)

        # Enviar un correo electrónico
        msg = MIMEMultipart()
        msg['From'] = 'teamclayton26@gmail.com'
        msg['To'] = CorreoElectronico
        msg['Subject'] = 'Confirmación de Reservación'
        message = '¡Reservación programada exitosamente!'
        msg.attach(MIMEText(message))

        mailserver = smtplib.SMTP('smtp.gmail.com', 587)
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.ehlo()
        mailserver.login('teamclayton26@gmail.com', 'beywfxlirstlutha')
        mailserver.sendmail('teamclayton26@gmail.com', CorreoElectronico, msg.as_string())
        mailserver.quit()

    except HTTPException:
        raise  # Si la excepción ya es HTTPException, la relanzamos
    except Exception as e:
        logger.error(f"Error al procesar formulario: {e}")
        raise HTTPException(status_code=500, detail="Error al procesar formulario")
    finally:
        db.close()

    return templates.TemplateResponse("confirmacion.html", {"request": request, "message": "¡Datos procesados exitosamente!"})

@app.get("/reservacion_del_dia/{fecha}")
async def reservacion_del_dia(fecha: str):
    fecha_formateada = datetime.strptime(fecha, "%Y-%m-%d").date()
    db = Session(bind=engine)
    try:
        # Usa alias 'reservaciones' para simplificar la referencia
        reservaciones_del_dia = db.execute(select(Reservaciones).where(Reservaciones.c.fecha == fecha_formateada)).all()
        reservaciones_json = [{
            'id': reserva.id,
            'NombreCompleto': reserva.NombreCompleto,
            'Telefono': reserva.Telefono,
            'ObjetivoFitness': reserva.ObjetivoFitness,
            'Disponibilidad': reserva.Disponibilidad,
            'InformacionSalud': reserva.InformacionSalud,
            'CorreoElectronico': reserva.CorreoElectronico
        } for reserva in reservaciones_del_dia]
        return JSONResponse(content=reservaciones_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/coaches", response_class=HTMLResponse)
async def coaches(request: Request):
    return templates.TemplateResponse("coaches.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")
