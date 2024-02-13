function verificarDisponibilidad() {
    var fechaCita = document.getElementById('FechaCita').value;
    var horaCita = document.getElementById('HoraCita').value;

    // Solo verifica la disponibilidad si ambos campos, fecha y hora, están llenos
    if (fechaCita && horaCita) {
        console.log(fechaCita);
        console.log('Enviando solicitud para verificar disponibilidad...');

        fetch('/cita_disponible', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'fecha': fechaCita,
                'hora': horaCita
            })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.disponible) {
                alert('Lo siento, esta fecha ya está reservada. Por favor, selecciona otra fecha.');
                document.getElementById('FechaCita').value = '';
                document.getElementById('HoraCita').value = '';
            } else {
                console.log('Fecha disponible. Puedes proceder con la reserva.');
            }
        })
        .catch(error => {
            console.error('Error en la solicitud:', error);
        });
    }
}
