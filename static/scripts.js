function verificarfechahora() {
    var fecha = document.getElementById('Fecha').value;
    var hora = document.getElementById('Hora').value;

    // Verificar que la fecha y la hora estén llenas
    if (fecha && hora) {
        var fechahora = fecha + ' ' + hora;

        console.log('Enviando solicitud para verificar disponibilidad de reservación...');

        fetch('/reservacion_disponible', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'Fecha': fecha,
                'Hora': hora
            })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.disponible) {
                alert('Lo siento, este horario ya está reservado. Por favor, selecciona otro horario.');
                document.getElementById('Disponibilidad').value = '';
            } else {
                console.log('Horario disponible. Puedes proceder con la reservación.');
            }
        })
        .catch(error => {
            console.error('Error en la solicitud:', error);
        });
    } else {
        console.log('Debe seleccionar una fecha y una hora antes de verificar la disponibilidad.');
    }
}

document.getElementById('siguiente').addEventListener('click', function() {
    // Llamar a la función verificarfechahora para verificar la disponibilidad de reservas
    verificarfechahora();

    // Mostrar el disclaimer y el botón de enviar
    document.getElementById('disclaimer').style.display = 'block';
    document.getElementById('enviar').style.display = 'inline-block';

    // Ocultar el botón de siguiente
    this.style.display = 'none';
});
