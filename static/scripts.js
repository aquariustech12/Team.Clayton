function verificarfechahora() {
    var fechahora = document.getElementById('ReservacionDisponible').value;

    // Solo verifica la disponibilidad si el campo de fecha y hora estan llenos
    if (fechahora) {
        console.log(fechahora);
        console.log('Enviando solicitud para verificar Reservacion Disponible...');

        fetch('/entrenamiento_disponible', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'ReservacionDisponible': fechahora
            })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.disponible) {
                alert('Lo siento, este horario ya está reservado. Por favor, selecciona otro horario.');
                document.getElementById('Disponibilidad').value = '';
            } else {
                console.log('Horario disponible. Puedes proceder con la reservacion.');
            }
        })
        .catch(error => {
            console.error('Error en la solicitud:', error);
        });
    }
}

document.getElementById('siguiente').addEventListener('click', function() {
    // Verificar que todos los campos del formulario están llenos
    // ...

    // Mostrar el disclaimer y el botón de enviar
    document.getElementById('disclaimer').style.display = 'block';
    document.getElementById('enviar').style.display = 'inline-block';

    // Ocultar el botón de siguiente
    this.style.display = 'none';
});
