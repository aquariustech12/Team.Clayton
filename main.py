import logging
from fastapi import FastAPI, HTTPException, Form, Request, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Boolean, Date, Time, select, update
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from datetime import datetime
from sqlalchemy.sql import and_
import pywhatkit
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logging.basicConfig(filename='error.log', level=logging.ERROR)
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
    Column('CorreoElectronico', String)
)
metadata.create_all(engine)
@app.on_event("startup")
async def startup_event():
    db = Session(bind=engine)
    try:
        # Añadir coaches a la base de datos
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
                  
        # Enviar un mensaje de WhatsApp
        
        pywhatkit.sendwhatmsg_instantly(Telefono, "¡Cita reservada exitosamente!", Fecha.Date, Hora.Time)

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
        print(f"Fecha: {Fecha}")  # Imprime la fecha recibida
        print(f"Hora: {Hora}")  # Imprime la hora recibida
        raise HTTPException(status_code=500, detail="Error al procesar formulario")
    finally:
        db.close()
    return templates.TemplateResponse("confirmacion.html", {"request": request, "message": "¡Datos procesados exitosamente!"})

@app.get("/reservacion_del_dia/{Fecha}")
async def reservacion_del_dia(fecha: str):
    fecha_formateada = datetime.strptime(fecha, "%Y-%m-%d").date()
    db = Session(bind=engine)
    try:
        # Usa alias 'reservaciones' para simplificar la referencia
        reservaciones_del_dia = db.execute(select(Reservaciones).where(Reservaciones.c.Fecha == fecha_formateada)).all()
        reservaciones_json = [{
            'id': Reservaciones.id,
            'NombreCompleto': Reservaciones.NombreCompleto,
            'Telefono': Reservaciones.Telefono,
            'ObjetivoFitness': Reservaciones.ObjetivoFitness,
            'Fecha': Reservaciones.Fecha.isoformat() if Reservaciones.Fecha else None,
            'Hora': Reservaciones.Hora.isoformat() if Reservaciones.Hora else None,
            'InformacionSalud': Reservaciones.InformacionSalud,
            'PreferenciasDieteticas': Reservaciones.PreferenciasDieteticas,
            'CorreoElectronico': Reservaciones.CorreoElectronico
        } for Reservaciones in reservaciones_del_dia]
        return JSONResponse(content=reservaciones_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/coaches", response_class=HTMLResponse)
async def coaches(request: Request):
    return templates.TemplateResponse("coaches.html", {"request": request})

@app.get("/disclaimer", response_class=HTMLResponse)
async def disclaimer(request: Request):
    return templates.TemplateResponse("disclaimer.html", {"request": request})

@app.post("/disclaimer")
async def generate_pdf():
    # Aquí es donde generarías el documento PDF. 
    # Por ahora, asumiremos que el documento ya existe y se llama "documento.pdf".
    return FileResponse("documento.pdf", media_type="application/pdf")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")