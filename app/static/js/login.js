// Evita el doble envío del formulario de login: Supabase Auth tarda unas
// décimas en responder y sin esto es fácil pulsar dos veces.
document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("loginForm");
    var boton = document.getElementById("btnLogin");

    if (!form || !boton) {
        return;
    }

    form.addEventListener("submit", function () {
        boton.disabled = true;
        boton.textContent = "Iniciando sesión…";
    });
});
