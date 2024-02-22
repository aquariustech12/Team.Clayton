function verificarfechahora() {
    var fecha = document.getElementById('Fecha').value;
    var hora = document.getElementById('Hora').value;

    // Verificar que la fecha y la hora estén llenas
    if (Fecha && Hora) {
        var Fecha, Hora = Fecha + ' ' + Hora;

        console.log('Enviando solicitud para verificar disponibilidad de reservación...');

        fetch('/reservacion_disponible', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'Fecha': Fecha,
                'Hora': Hora
            })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.Reservado) {
                alert('Lo siento, este horario ya está reservado. Por favor, selecciona otro horario.');
                document.getElementById('Reservado').value = '';
            } else {
                console.log('Horario disponible. Puedes proceder con la reservación.');
            }
        })
        .catch(error => {
            console.error('Error en la solicitud:', error);
        });
    } else {
        console.log('Debe seleccionar una fecha y una hora antes de verificar la reservación.');
    }
}

document.getElementById('Términos y Condiciones').addEventListener('click', function() {
    // Llamar a la función verificarfechahora para verificar la disponibilidad de reservas
    verificarfechahora();
});
